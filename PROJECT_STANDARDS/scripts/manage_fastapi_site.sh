#!/usr/bin/env bash
set -euo pipefail

PROJECT_PATH="${PROJECT_PATH:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)}"
API_DIR="${API_DIR:-$PROJECT_PATH/apps/api}"
APP_ID="${APP_ID:-app}"
APP_NAME="${APP_NAME:-App}"
APP_MODULE="${APP_MODULE:-app_api.main:app}"
APP_PACKAGE="${APP_PACKAGE:-${APP_MODULE%%.*}}"
DEFAULT_PORT="${DEFAULT_PORT:-8000}"
HEALTH_PATH="${HEALTH_PATH:-/health}"

VENV_DIR="${VENV_DIR:-$PROJECT_PATH/venv}"
ENV_FILE="${ENV_FILE:-$PROJECT_PATH/.env}"
ENV_EXAMPLE_FILE="${ENV_EXAMPLE_FILE:-$PROJECT_PATH/.env.example}"
LOG_DIR="${LOG_DIR:-$PROJECT_PATH/logs}"
DATA_DIR="${DATA_DIR:-$PROJECT_PATH/data}"

PID_FILE="${PID_FILE:-$LOG_DIR/$APP_ID.pid}"
LOG_FILE="${LOG_FILE:-$LOG_DIR/$APP_ID.log}"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-$DEFAULT_PORT}"
WORKERS="${WORKERS:-1}"
PYTHON_BIN="${PYTHON_BIN:-}"

info()  { printf '\033[0;32m[INFO]\033[0m  %s\n' "$*"; }
warn()  { printf '\033[0;33m[WARN]\033[0m  %s\n' "$*"; }
error() { printf '\033[0;31m[ERROR]\033[0m %s\n' "$*" >&2; }
die()   { error "$*"; exit 1; }

if [ ! -d "$API_DIR" ]; then
  die "apps/api 目录不存在: $API_DIR"
fi

load_env() {
  if [ -f "$ENV_FILE" ]; then
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
  fi
  PORT="${PORT:-$DEFAULT_PORT}"
}

ensure_dirs() {
  mkdir -p "$DATA_DIR" "$LOG_DIR"
}

resolve_python_bin() {
  if [ -n "$PYTHON_BIN" ] && [ -x "$PYTHON_BIN" ]; then
    return
  fi

  if [ -x "$VENV_DIR/bin/python" ]; then
    PYTHON_BIN="$VENV_DIR/bin/python"
    return
  fi

  if command -v python >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python)"
    return
  fi

  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
    return
  fi

  die "找不到可用的 python3 解释器"
}

ensure_venv() {
  local creator
  creator="${PYTHON_BIN:-}"
  if [ -z "$creator" ] || [ ! -x "$creator" ] || [ "$creator" = "$VENV_DIR/bin/python" ]; then
    if command -v python >/dev/null 2>&1; then
      creator="$(command -v python)"
    elif command -v python3 >/dev/null 2>&1; then
      creator="$(command -v python3)"
    else
      die "无法创建虚拟环境，系统缺少 python 解释器"
    fi
  fi

  if [ ! -d "$VENV_DIR" ]; then
    info "创建虚拟环境: $VENV_DIR"
    "$creator" -m venv "$VENV_DIR"
  fi
  PYTHON_BIN="$VENV_DIR/bin/python"
}

require_runtime() {
  if ! (
    cd "$API_DIR" &&
      PYTHONPATH=src "$PYTHON_BIN" -c "import fastapi, sqlalchemy, uvicorn, alembic, $APP_PACKAGE" >/dev/null 2>&1
  ); then
    die "运行时依赖未就绪，请先执行 ./$APP_ID.sh install"
  fi
}

install_cmd() {
  load_env
  ensure_dirs
  resolve_python_bin
  ensure_venv
  info "安装 $APP_NAME 依赖"
  (
    cd "$API_DIR"
    "$PYTHON_BIN" -m pip install --upgrade pip
    "$PYTHON_BIN" -m pip install -e ".[dev]"
  )
  info "依赖安装完成"
}

init_env_cmd() {
  if [ -f "$ENV_FILE" ]; then
    warn ".env 已存在: $ENV_FILE"
    return 0
  fi
  if [ ! -f "$ENV_EXAMPLE_FILE" ]; then
    die "缺少 .env.example: $ENV_EXAMPLE_FILE"
  fi
  cp "$ENV_EXAMPLE_FILE" "$ENV_FILE"
  info "已创建 .env: $ENV_FILE"
}

run_migrations() {
  require_runtime
  info "应用数据库迁移 (alembic upgrade head)"
  (
    cd "$API_DIR"
    PYTHONPATH=src "$PYTHON_BIN" -m alembic upgrade head
  )
}

db_current_cmd() {
  load_env
  ensure_dirs
  resolve_python_bin
  require_runtime
  (
    cd "$API_DIR"
    PYTHONPATH=src "$PYTHON_BIN" -m alembic current
  )
}

list_listening_pids() {
  lsof -nP -iTCP:"$PORT" -sTCP:LISTEN -t 2>/dev/null | awk '!seen[$0]++' || true
}

pid_command() {
  ps -o command= -p "$1" 2>/dev/null || true
}

is_project_pid() {
  local pid="$1"
  local cmd
  cmd="$(pid_command "$pid")"
  if [ -z "$cmd" ]; then
    return 1
  fi
  case "$cmd" in
    *"$PROJECT_PATH"*|*"$APP_MODULE"*|*"$APP_PACKAGE"*)
      return 0
      ;;
  esac
  return 1
}

is_running() {
  if [ -f "$PID_FILE" ]; then
    local pid
    pid="$(cat "$PID_FILE" 2>/dev/null || true)"
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      return 0
    fi
  fi
  return 1
}

wait_for_health() {
  local retries=40
  while [ "$retries" -gt 0 ]; do
    if curl -fsS --max-time 2 "http://127.0.0.1:$PORT$HEALTH_PATH" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.25
    retries=$((retries - 1))
  done
  return 1
}

force_stop_port_listeners() {
  local pids
  pids="$(list_listening_pids)"
  [ -z "$pids" ] && return 0

  warn "端口 $PORT 被占用，尝试停止监听进程: $pids"
  kill $pids 2>/dev/null || true
  sleep 1

  pids="$(list_listening_pids)"
  if [ -n "$pids" ]; then
    warn "优雅停止超时，强制终止端口 $PORT 进程: $pids"
    kill -9 $pids 2>/dev/null || true
    sleep 1
  fi

  pids="$(list_listening_pids)"
  [ -z "$pids" ] || die "无法释放端口 $PORT"
}

start_cmd() {
  load_env
  ensure_dirs
  resolve_python_bin
  require_runtime

  if is_running; then
    info "$APP_NAME 已运行 (PID=$(cat "$PID_FILE"))"
    return 0
  fi

  rm -f "$PID_FILE"
  force_stop_port_listeners
  run_migrations
  : > "$LOG_FILE"

  info "启动 $APP_NAME: $HOST:$PORT"
  (
    cd "$API_DIR"
    PYTHONPATH=src nohup "$PYTHON_BIN" -m uvicorn "$APP_MODULE" \
      --host "$HOST" \
      --port "$PORT" \
      --workers "$WORKERS" \
      >>"$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
  )

  if wait_for_health; then
    info "启动成功 (PID=$(cat "$PID_FILE"))"
    info "日志: $LOG_FILE"
    return 0
  fi

  error "启动失败，请检查日志: $LOG_FILE"
  tail -n 40 "$LOG_FILE" || true
  return 1
}

stop_cmd() {
  load_env
  if ! is_running; then
    if [ -n "$(list_listening_pids)" ]; then
      force_stop_port_listeners
    else
      warn "$APP_NAME 未运行"
    fi
    rm -f "$PID_FILE"
    return 0
  fi

  local pid
  pid="$(cat "$PID_FILE")"
  kill "$pid" 2>/dev/null || true
  sleep 1

  if kill -0 "$pid" 2>/dev/null; then
    warn "常规停止超时，强制终止 PID=$pid"
    kill -9 "$pid" 2>/dev/null || true
  fi
  rm -f "$PID_FILE"

  local extra_pids
  extra_pids="$(list_listening_pids)"
  if [ -n "$extra_pids" ]; then
    force_stop_port_listeners
  fi
  info "$APP_NAME 已停止"
}

status_cmd() {
  load_env
  if is_running; then
    echo "running pid=$(cat "$PID_FILE") port=$PORT"
  else
    echo "stopped port=$PORT"
  fi
}

restart_cmd() {
  stop_cmd
  start_cmd
}

logs_cmd() {
  ensure_dirs
  touch "$LOG_FILE"
  tail -f "$LOG_FILE"
}

ip_cmd() {
  load_env
  echo "http://localhost:$PORT"
  local lan_ip
  lan_ip="$(ifconfig | awk '/inet / && $2 != "127.0.0.1" {print $2; exit}')"
  if [ -n "$lan_ip" ]; then
    echo "http://$lan_ip:$PORT"
  fi
}

check_cmd() {
  load_env
  ensure_dirs
  resolve_python_bin
  require_runtime
  (
    cd "$API_DIR"
    PYTHONPATH=src "$PYTHON_BIN" -m compileall -q "src/$APP_PACKAGE"
    PYTHONPATH=src "$PYTHON_BIN" -m pytest -q
  )
}

test_cmd() {
  check_cmd
}

update_cmd() {
  install_cmd
}

resolve_python_bin

case "${1:-}" in
  install) install_cmd ;;
  init-env) init_env_cmd ;;
  db-upgrade) load_env; ensure_dirs; resolve_python_bin; run_migrations ;;
  db-current) db_current_cmd ;;
  start) start_cmd ;;
  stop) stop_cmd ;;
  restart) restart_cmd ;;
  status) status_cmd ;;
  logs) logs_cmd ;;
  ip) ip_cmd ;;
  check) check_cmd ;;
  test) test_cmd ;;
  update) update_cmd ;;
  *)
    echo "Usage: $0 {install|init-env|db-upgrade|db-current|start|stop|restart|status|logs|ip|check|test|update}"
    exit 1
    ;;
esac

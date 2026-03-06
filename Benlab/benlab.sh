#!/usr/bin/env bash
set -euo pipefail

PROJECT_PATH="${PROJECT_PATH:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)}"
API_DIR="$PROJECT_PATH/apps/api"
VENV_DIR="${VENV_DIR:-$PROJECT_PATH/venv}"
ENV_FILE="${ENV_FILE:-$PROJECT_PATH/.env}"
LOG_DIR="${LOG_DIR:-$PROJECT_PATH/logs}"

PID_FILE="${PID_FILE:-$LOG_DIR/benlab.pid}"
LOG_FILE="${LOG_FILE:-$LOG_DIR/benlab.log}"
ACCESS_LOG_FILE="${ACCESS_LOG_FILE:-$LOG_DIR/benlab-access.log}"

HOST="${HOST:-${BIND_HOST:-0.0.0.0}}"
PORT="${PORT:-${UVICORN_PORT:-9000}}"
APP_MODULE="${APP_MODULE:-benlab_api.main:app}"
APP_KEY="${APP_KEY:-${APP_MODULE%%.*}}"
WORKER_CLASS="${WORKER_CLASS:-uvicorn.workers.UvicornWorker}"
TIMEOUT="${TIMEOUT:-120}"
WORKERS="${WORKERS:-}"

info() { echo "[INFO] $1"; }
warn() { echo "[WARN] $1"; }
error() { echo "[ERROR] $1"; }

if [ ! -d "$API_DIR" ]; then
  error "apps/api 目录不存在: $API_DIR"
  exit 1
fi

load_env() {
  if [ -f "$ENV_FILE" ]; then
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
  fi
}

ensure_venv() {
  if [ ! -d "$VENV_DIR" ]; then
    info "创建虚拟环境: $VENV_DIR"
    python3 -m venv "$VENV_DIR"
  fi
}

activate_venv() {
  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"
}

ensure_deps() {
  if ! (cd "$API_DIR" && PYTHONPATH=src python -c "import benlab_api, fastapi, sqlalchemy, gunicorn" >/dev/null 2>&1); then
    info "安装/更新依赖"
    (cd "$API_DIR" && python -m pip install --upgrade pip && python -m pip install -e '.[dev]')
  fi
}

calc_workers() {
  if [ -n "$WORKERS" ]; then
    echo "$WORKERS"
    return
  fi
  python - <<'PY'
import multiprocessing
cores = multiprocessing.cpu_count()
print(max(2, min(8, cores * 2 + 1)))
PY
}

is_running() {
  if [ -f "$PID_FILE" ]; then
    local pid
    pid=$(cat "$PID_FILE" 2>/dev/null || true)
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      return 0
    fi
  fi
  return 1
}

wait_for_pid() {
  local retries=40
  while [ "$retries" -gt 0 ]; do
    if is_running; then
      return 0
    fi
    sleep 0.25
    retries=$((retries - 1))
  done
  return 1
}

list_listening_pids() {
  lsof -nP -iTCP:"$PORT" -sTCP:LISTEN -t 2>/dev/null | awk '!seen[$0]++'
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
    *"$PROJECT_PATH"*|*"$APP_MODULE"*|*"$APP_KEY"*)
      return 0
      ;;
  esac
  return 1
}

collect_project_port_pids() {
  local pid
  while read -r pid; do
    [ -n "$pid" ] || continue
    if is_project_pid "$pid"; then
      printf '%s\n' "$pid"
    fi
  done < <(list_listening_pids)
}

wait_for_port_release() {
  local retries=40
  while [ "$retries" -gt 0 ]; do
    if [ -z "$(list_listening_pids)" ]; then
      return 0
    fi
    sleep 0.25
    retries=$((retries - 1))
  done
  return 1
}

stop_port_listeners_if_owned() {
  local owned_pids=()
  local pid

  while read -r pid; do
    [ -n "$pid" ] || continue
    owned_pids+=("$pid")
  done < <(collect_project_port_pids)

  if [ "${#owned_pids[@]}" -eq 0 ]; then
    return 1
  fi

  warn "PID 文件缺失或过期，正在停止端口 $PORT 上的项目进程: ${owned_pids[*]}"
  kill "${owned_pids[@]}" 2>/dev/null || true

  if wait_for_port_release; then
    info "端口 $PORT 监听进程已停止"
    return 0
  fi

  warn "优雅停止超时，强制终止端口 $PORT 进程: ${owned_pids[*]}"
  kill -9 "${owned_pids[@]}" 2>/dev/null || true

  if wait_for_port_release; then
    info "端口 $PORT 监听进程已强制停止"
    return 0
  fi
  return 1
}

check_port_free() {
  if [ -n "$(list_listening_pids)" ]; then
    error "端口被占用: $PORT"
    if [ -n "$(collect_project_port_pids)" ]; then
      warn "该端口疑似被本项目进程占用，请先执行 './benlab.sh stop'"
    fi
    lsof -nP -iTCP:"$PORT" -sTCP:LISTEN || true
    exit 1
  fi
}

install_cmd() {
  ensure_venv
  activate_venv
  (cd "$API_DIR" && python -m pip install --upgrade pip && python -m pip install -e '.[dev]')
  info "依赖安装完成"
}

start() {
  load_env
  ensure_venv
  activate_venv
  ensure_deps

  if is_running; then
    local pid
    pid=$(cat "$PID_FILE")
    warn "服务已运行 (PID=$pid)"
    return 0
  fi

  rm -f "$PID_FILE"
  check_port_free

  local workers
  workers=$(calc_workers)
  mkdir -p "$LOG_DIR"
  : > "$LOG_FILE"
  : > "$ACCESS_LOG_FILE"

  info "启动 Benlab: $HOST:$PORT workers=$workers"
  (
    cd "$API_DIR"
    PYTHONPATH=src python -m gunicorn "$APP_MODULE" \
      --bind "$HOST:$PORT" \
      --workers "$workers" \
      --worker-class "$WORKER_CLASS" \
      --timeout "$TIMEOUT" \
      --pid "$PID_FILE" \
      --daemon \
      --log-file "$LOG_FILE" \
      --access-logfile "$ACCESS_LOG_FILE" \
      --capture-output
  )

  if wait_for_pid; then
    info "启动成功 (PID=$(cat "$PID_FILE"))"
    info "日志: $LOG_FILE"
    return 0
  fi

  error "启动失败，请检查日志: $LOG_FILE"
  return 1
}

stop() {
  if ! is_running; then
    if stop_port_listeners_if_owned; then
      rm -f "$PID_FILE"
      return 0
    fi
    if [ -n "$(list_listening_pids)" ]; then
      warn "未检测到 PID 文件对应进程，且端口 $PORT 被非本项目进程占用"
      lsof -nP -iTCP:"$PORT" -sTCP:LISTEN || true
    else
      warn "服务未运行"
    fi
    rm -f "$PID_FILE"
    return 0
  fi

  local pid
  pid=$(cat "$PID_FILE")
  kill "$pid" || true

  local retries=40
  while [ "$retries" -gt 0 ]; do
    if ! kill -0 "$pid" 2>/dev/null; then
      rm -f "$PID_FILE"
      info "已停止"
      return 0
    fi
    sleep 0.25
    retries=$((retries - 1))
  done

  warn "常规停止超时，强制终止 PID=$pid"
  kill -9 "$pid" || true
  rm -f "$PID_FILE"
  stop_port_listeners_if_owned || true
}

status() {
  if is_running; then
    echo "running pid=$(cat "$PID_FILE") port=$PORT"
  else
    echo "stopped"
  fi
}

restart() {
  stop
  start
}

logs() {
  mkdir -p "$LOG_DIR"
  touch "$LOG_FILE" "$ACCESS_LOG_FILE"
  tail -f "$LOG_FILE" "$ACCESS_LOG_FILE"
}

ip() {
  echo "http://localhost:$PORT"
  local lan_ip
  lan_ip=$(ifconfig | awk '/inet / && $2 != "127.0.0.1" {print $2; exit}')
  if [ -n "$lan_ip" ]; then
    echo "http://$lan_ip:$PORT"
  fi
}

update() {
  if [ ! -d "$PROJECT_PATH/.git" ]; then
    error "当前目录不是 git 仓库，无法 update"
    exit 1
  fi
  local was_running=0
  if is_running; then
    was_running=1
    stop
  fi
  git -C "$PROJECT_PATH" pull --ff-only
  install_cmd
  if [ "$was_running" -eq 1 ]; then
    start
  fi
}

case "${1:-}" in
  install) install_cmd ;;
  start) start ;;
  stop) stop ;;
  restart) restart ;;
  status) status ;;
  logs) logs ;;
  ip) ip ;;
  update) update ;;
  *)
    echo "用法: $0 {install|start|stop|restart|status|logs|ip|update}"
    exit 1
    ;;
esac

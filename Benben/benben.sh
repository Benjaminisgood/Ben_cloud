#!/usr/bin/env bash
# Benben 服务管理脚本
# 用法: ./benben.sh {install|start|stop|restart|status|logs|ip|check|init-env|update}
set -euo pipefail

PROJECT_PATH="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
VENV_DIR="${VENV_DIR:-$PROJECT_PATH/venv}"
ENV_FILE="$PROJECT_PATH/.env"
ENV_EXAMPLE_FILE="$PROJECT_PATH/.env.example"
LOG_DIR="$PROJECT_PATH/logs"
PID_FILE="$LOG_DIR/benben.pid"
LOG_FILE="$LOG_DIR/benben.log"

info()  { printf '\033[0;32m[INFO]\033[0m  %s\n' "$*"; }
warn()  { printf '\033[0;33m[WARN]\033[0m  %s\n' "$*"; }
error() { printf '\033[0;31m[ERROR]\033[0m %s\n' "$*" >&2; }

REQUIRED_ENV_KEYS=(
  "BENBEN_OSS_ENDPOINT"
  "BENBEN_OSS_ACCESS_KEY_ID"
  "BENBEN_OSS_ACCESS_KEY_SECRET"
  "BENBEN_OSS_BUCKET_NAME"
  "BENBEN_SSO_SECRET"
  "BENBEN_SESSION_SECRET_KEY"
)

_read_env_key() {
  local file="$1" key="$2"
  [ -f "$file" ] || return 0
  awk -F= -v k="$key" '
    /^[[:space:]]*#/{next}
    $1==k {
      v=$0; sub(/^[^=]*=/,"",v)
      gsub(/^[[:space:]]+|[[:space:]]+$/,"",v)
      if (v~/^".*"$/)       { sub(/^"/,"",v); sub(/"$/,"",v) }
      if (v~/^\x27.*\x27$/) { sub(/^\x27/,"",v); sub(/\x27$/,"",v) }
      print v; exit
    }
  ' "$file"
}

get_python() {
  if [ -x /Users/ben/miniforge3/bin/python ]; then
    echo "/Users/ben/miniforge3/bin/python"
  elif command -v python3 >/dev/null 2>&1; then
    command -v python3
  else
    command -v python
  fi
}

load_env() {
  [ -f "$ENV_FILE" ] || return 0
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
}

_env_value() {
  local key="$1" value="${!key:-}"
  if [ -n "$value" ]; then
    printf '%s' "$value"
    return 0
  fi
  _read_env_key "$ENV_FILE" "$key"
}

ensure_runtime_env() {
  local key value
  local missing=()
  for key in "${REQUIRED_ENV_KEYS[@]}"; do
    value="$(_env_value "$key")"
    if [ -z "$value" ]; then
      missing+=("$key")
    fi
  done

  if [ "${#missing[@]}" -gt 0 ]; then
    error "缺少必需环境变量: ${missing[*]}"
    if [ ! -f "$ENV_FILE" ]; then
      error "未找到 ${ENV_FILE}，请先执行：./benben.sh init-env 并补全密钥"
    else
      error "请补全 ${ENV_FILE} 中的必需配置后再启动"
    fi
    return 1
  fi
  return 0
}

PYTHON_BIN="$(get_python)"
PORT="${BENBEN_PORT:-$(_read_env_key "$ENV_FILE" BENBEN_PORT)}"
PORT="${PORT:-8600}"

mkdir -p "$LOG_DIR"
load_env
PORT="${BENBEN_PORT:-$PORT}"

ensure_venv() {
  if [ ! -x "$VENV_DIR/bin/python" ]; then
    info "创建虚拟环境: $VENV_DIR"
    "$PYTHON_BIN" -m venv "$VENV_DIR"
  fi
}

ensure_deps() {
  if ! (cd "$PROJECT_PATH" && PYTHONPATH=. "$VENV_DIR/bin/python" -c "import fastapi, uvicorn, itsdangerous" >/dev/null 2>&1); then
    info "安装/更新依赖"
    (
      cd "$PROJECT_PATH/apps/api"
      "$VENV_DIR/bin/python" -m pip install -q --upgrade pip
      "$VENV_DIR/bin/python" -m pip install -q -e ".[dev]"
    )
  fi
}

is_running() {
  [ -f "$PID_FILE" ] || return 1
  local pid
  pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null
}

port_listener_pid() {
  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"$PORT" -sTCP:LISTEN -t 2>/dev/null | head -1
  else
    echo ""
  fi
}

port_listener_pids() {
  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"$PORT" -sTCP:LISTEN -t 2>/dev/null | awk '!seen[$0]++'
  else
    echo ""
  fi
}

force_stop_port_listeners() {
  local pids
  pids="$(port_listener_pids || true)"
  [ -z "$pids" ] && return 0

  warn "端口 $PORT 被进程占用 ($pids)，正在终止"
  lsof -nP -iTCP:"$PORT" -sTCP:LISTEN || true
  kill $pids 2>/dev/null || true
  sleep 0.5

  pids="$(port_listener_pids || true)"
  if [ -z "$pids" ]; then
    info "端口 $PORT 已释放"
    return 0
  fi

  warn "优雅停止超时，强制终止端口 $PORT 进程: $pids"
  kill -9 $pids 2>/dev/null || true
  sleep 0.5

  pids="$(port_listener_pids || true)"
  if [ -z "$pids" ]; then
    info "端口 $PORT 已强制释放"
    return 0
  fi

  error "无法释放端口 $PORT"
  lsof -nP -iTCP:"$PORT" -sTCP:LISTEN || true
  exit 1
}

wait_health() {
  local retries=30
  while [ "$retries" -gt 0 ]; do
    if curl -fsS --max-time 1 "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.3
    retries=$((retries - 1))
  done
  return 1
}

cmd_install() {
  ensure_venv
  info "安装依赖"
  (
    cd "$PROJECT_PATH/apps/api"
    "$VENV_DIR/bin/python" -m pip install -q --upgrade pip
    "$VENV_DIR/bin/python" -m pip install -q -e ".[dev]"
  )
  info "依赖安装完成"
}

cmd_start() {
  ensure_runtime_env || exit 1
  ensure_venv
  ensure_deps

  if is_running; then
    local pid
    pid="$(cat "$PID_FILE")"
    info "benben running pid=$pid port=$PORT"
    return 0
  fi

  force_stop_port_listeners

  info "启动 Benben (port=$PORT)"
  (
    cd "$PROJECT_PATH"
    BENBEN_PORT="$PORT" nohup "$VENV_DIR/bin/python" app.py >>"$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
  )

  if wait_health; then
    local pid
    pid="$(cat "$PID_FILE")"
    info "benben running pid=$pid port=$PORT"
  else
    error "benben start failed port=$PORT"
    [ -f "$LOG_FILE" ] && tail -n 30 "$LOG_FILE" >&2 || true
    exit 1
  fi
}

cmd_stop() {
  if ! is_running; then
    force_stop_port_listeners
    info "benben stopped port=$PORT"
    rm -f "$PID_FILE"
    return 0
  fi

  local pid
  pid="$(cat "$PID_FILE")"
  kill "$pid" 2>/dev/null || true
  sleep 0.5
  if kill -0 "$pid" 2>/dev/null; then
    kill -9 "$pid" 2>/dev/null || true
  fi
  rm -f "$PID_FILE"
  force_stop_port_listeners
  info "benben stopped port=$PORT"
}

cmd_status() {
  if is_running; then
    local pid
    pid="$(cat "$PID_FILE")"
    echo "running pid=$pid port=$PORT"
  else
    if [ -f "$PID_FILE" ]; then
      rm -f "$PID_FILE"
    fi
    echo "stopped port=$PORT"
  fi
}

cmd_logs() {
  touch "$LOG_FILE"
  tail -f "$LOG_FILE"
}

cmd_ip() {
  echo "http://localhost:$PORT"
}

cmd_check() {
  ensure_venv
  ensure_deps
  info "执行 Benben 自检"
  (cd "$PROJECT_PATH" && "$VENV_DIR/bin/python" -m compileall -q app.py apps)
  info "代码编译检查通过"

  if curl -fsS --max-time 2 "http://127.0.0.1:$PORT/health/ready" >/dev/null 2>&1; then
    info "运行时健康检查通过 port=$PORT"
  else
    warn "健康检查未通过（服务可能未启动），请先执行 ./benben.sh start"
  fi
}

cmd_init_env() {
  if [ -f "$ENV_FILE" ]; then
    info ".env 已存在：$ENV_FILE"
    return 0
  fi
  if [ ! -f "$ENV_EXAMPLE_FILE" ]; then
    error "未找到模板文件：$ENV_EXAMPLE_FILE"
    exit 1
  fi
  cp "$ENV_EXAMPLE_FILE" "$ENV_FILE"
  info "已生成配置文件：$ENV_FILE"
  warn "请先补全 OSS 与 SSO 相关密钥后再执行 ./benben.sh start"
}

cmd_restart() {
  cmd_stop
  cmd_start
}

cmd_update() {
  cmd_install
}

case "${1:-}" in
  install) cmd_install ;;
  start) cmd_start ;;
  stop) cmd_stop ;;
  restart) cmd_restart ;;
  status) cmd_status ;;
  logs) cmd_logs ;;
  ip) cmd_ip ;;
  check) cmd_check ;;
  init-env) cmd_init_env ;;
  update) cmd_update ;;
  *)
    echo "Usage: $0 {install|start|stop|restart|status|logs|ip|check|init-env|update}"
    exit 1
    ;;
esac

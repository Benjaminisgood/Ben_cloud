#!/usr/bin/env bash
# Benben 服务管理脚本
# 用法: ./benben.sh {install|start|stop|restart|status|logs|ip|check|init-env|update}
set -euo pipefail

PROJECT_PATH="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
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
  info "安装依赖"
  (
    cd "$PROJECT_PATH/apps/api"
    "$PYTHON_BIN" -m pip install -q --upgrade pip
    "$PYTHON_BIN" -m pip install -q -e ".[dev]"
  )
  info "依赖安装完成"
}

cmd_start() {
  ensure_runtime_env || exit 1

  if is_running; then
    local pid
    pid="$(cat "$PID_FILE")"
    info "benben running pid=$pid port=$PORT"
    return 0
  fi

  local occupy_pid
  occupy_pid="$(port_listener_pid || true)"
  if [ -n "$occupy_pid" ]; then
    warn "端口 $PORT 已被占用（pid=${occupy_pid}），尝试继续启动可能失败"
  fi

  info "启动 Benben (port=$PORT)"
  (
    cd "$PROJECT_PATH"
    BENBEN_PORT="$PORT" nohup "$PYTHON_BIN" app.py >>"$LOG_FILE" 2>&1 &
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
  info "执行 Benben 自检"
  (cd "$PROJECT_PATH" && "$PYTHON_BIN" -m compileall -q app.py apps)
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

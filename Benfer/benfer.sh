#!/usr/bin/env bash
set -euo pipefail

PROJECT_PATH="${PROJECT_PATH:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)}"
API_DIR="$PROJECT_PATH/apps/api"
VENV_DIR="${VENV_DIR:-$PROJECT_PATH/venv}"
ENV_FILE="${ENV_FILE:-$PROJECT_PATH/.env}"
LOG_DIR="${LOG_DIR:-$PROJECT_PATH/logs}"
DATA_DIR="${DATA_DIR:-$PROJECT_PATH/data}"

PID_FILE="${PID_FILE:-$LOG_DIR/benfer.pid}"
LOG_FILE="${LOG_FILE:-$LOG_DIR/error.log}"
ACCESS_LOG_FILE="${ACCESS_LOG_FILE:-$LOG_DIR/access.log}"

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8500}"
APP_MODULE="${APP_MODULE:-benfer_api.main:app}"
APP_KEY="${APP_KEY:-${APP_MODULE%%.*}}"
WORKER_CLASS="${WORKER_CLASS:-uvicorn.workers.UvicornWorker}"
TIMEOUT="${TIMEOUT:-120}"
WORKERS="${WORKERS:-4}"
PYTHON_BIN="${PYTHON_BIN:-}"

info()  { printf '\033[0;32m[INFO]\033[0m  %s\n' "$*"; }
warn()  { printf '\033[0;33m[WARN]\033[0m  %s\n' "$*"; }
error() { printf '\033[0;31m[ERROR]\033[0m %s\n' "$*" >&2; }
die()   { error "$*"; exit 1; }

if [ ! -d "$API_DIR" ]; then
  die "apps/api directory not found: $API_DIR"
fi

resolve_python_bin() {
  if [ -n "$PYTHON_BIN" ]; then
    return
  fi

  if command -v python3.12 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3.12)"
    return
  fi

  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
    return
  fi

  die "python3 interpreter not found"
}

load_env() {
  if [ -f "$ENV_FILE" ]; then
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
  fi
}

ensure_dirs() {
  mkdir -p "$DATA_DIR" "$LOG_DIR"
}

ensure_venv() {
  local venv_python="$VENV_DIR/bin/python"
  local expected_version
  local current_version=""

  expected_version="$("$PYTHON_BIN" -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')"

  if [ ! -d "$VENV_DIR" ]; then
    info "Creating virtualenv: $VENV_DIR"
    "$PYTHON_BIN" -m venv "$VENV_DIR"
  fi

  if [ -x "$venv_python" ]; then
    current_version="$("$venv_python" -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")' 2>/dev/null || true)"
  fi

  if [ ! -x "$venv_python" ] || [ -z "$current_version" ] || [ "$current_version" != "$expected_version" ]; then
    warn "Virtualenv is invalid or uses Python $current_version (expected $expected_version), recreating: $VENV_DIR"
    "$PYTHON_BIN" -m venv --clear "$VENV_DIR"
  fi
}

activate_venv() {
  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"
}

ensure_deps() {
  local venv_python="$VENV_DIR/bin/python"
  if ! "$venv_python" -c "import benfer_api, fastapi, sqlalchemy, gunicorn" >/dev/null 2>&1; then
    info "Installing/updating dependencies"
    "$venv_python" -m pip install -q --upgrade pip
    "$venv_python" -m pip install -q -e "$API_DIR"
  fi
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

check_port_free() {
  if [ -n "$(list_listening_pids)" ]; then
    error "Port in use: $PORT"
    if [ -n "$(collect_project_port_pids)" ]; then
      warn "Port appears to be occupied by this project; run './benfer.sh stop' first."
    fi
    lsof -nP -iTCP:"$PORT" -sTCP:LISTEN || true
    exit 1
  fi
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

  warn "PID file missing/stale, stopping app process(es) on port $PORT: ${owned_pids[*]}"
  kill "${owned_pids[@]}" 2>/dev/null || true
  sleep 1

  local still_listening
  still_listening="$(list_listening_pids)"
  if [ -n "$still_listening" ]; then
    kill -9 "${owned_pids[@]}" 2>/dev/null || true
    sleep 1
  fi

  if [ -z "$(list_listening_pids)" ]; then
    info "Stopped listener(s) on port $PORT"
    return 0
  fi
  return 1
}

install_cmd() {
  load_env
  ensure_dirs
  ensure_venv
  activate_venv
  "$VENV_DIR/bin/python" -m pip install -q --upgrade pip
  "$VENV_DIR/bin/python" -m pip install -q -e "$API_DIR[dev]"
  info "Dependencies installed"
}

start() {
  load_env
  ensure_dirs
  ensure_venv
  activate_venv
  ensure_deps

  if is_running; then
    local pid
    pid=$(cat "$PID_FILE")
    warn "Service is already running (PID=$pid)"
    return 0
  fi

  rm -f "$PID_FILE"
  check_port_free

  : > "$LOG_FILE"
  : > "$ACCESS_LOG_FILE"

  info "Starting Benfer: $HOST:$PORT"
  (
    cd "$PROJECT_PATH"
    export PYTHONPATH="$PROJECT_PATH/apps/api/src:${PYTHONPATH:-}"
    exec "$VENV_DIR/bin/gunicorn" \
      -w "$WORKERS" \
      -k "$WORKER_CLASS" \
      -b "$HOST:$PORT" \
      --timeout "$TIMEOUT" \
      --pid "$PID_FILE" \
      --daemon \
      --access-logfile "$ACCESS_LOG_FILE" \
      --error-logfile "$LOG_FILE" \
      --capture-output \
      --enable-stdio-inheritance \
      "$APP_MODULE"
  )

  if wait_for_pid; then
    info "Started (PID=$(cat "$PID_FILE"))"
    info "Logs: $LOG_FILE | $ACCESS_LOG_FILE"
    return 0
  fi

  error "Failed to start, check logs: $LOG_FILE"
  return 1
}

stop() {
  if ! is_running; then
    if stop_port_listeners_if_owned; then
      rm -f "$PID_FILE"
      return 0
    fi
    if [ -n "$(list_listening_pids)" ]; then
      warn "Service PID is not tracked, and port $PORT is occupied by a non-project process."
      lsof -nP -iTCP:"$PORT" -sTCP:LISTEN || true
    else
      warn "Service is not running"
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
      info "Stopped"
      return 0
    fi
    sleep 0.25
    retries=$((retries - 1))
  done

  warn "Stop timeout, force kill PID=$pid"
  kill -9 "$pid" || true
  rm -f "$PID_FILE"
  stop_port_listeners_if_owned || true
}

status() {
  load_env
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
  load_env
  ensure_dirs
  touch "$LOG_FILE" "$ACCESS_LOG_FILE"
  tail -f "$LOG_FILE" "$ACCESS_LOG_FILE"
}

ip() {
  load_env
  echo "http://localhost:$PORT"
  local lan_ip
  lan_ip=$(ifconfig | awk '/inet / && $2 != "127.0.0.1" {print $2; exit}')
  if [ -n "$lan_ip" ]; then
    echo "http://$lan_ip:$PORT"
  fi
}

update() {
  local was_running=0
  if is_running; then
    was_running=1
    stop
  fi
  install_cmd
  if [ "$was_running" -eq 1 ]; then
    start
  fi
}

resolve_python_bin

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
    echo "Usage: $0 {install|start|stop|restart|status|logs|ip|update}"
    exit 1
    ;;
esac

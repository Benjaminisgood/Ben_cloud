#!/usr/bin/env bash
set -euo pipefail

PROJECT_PATH="${PROJECT_PATH:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)}"
API_DIR="$PROJECT_PATH/apps/api"
VENV_DIR="${VENV_DIR:-$PROJECT_PATH/venv}"
ENV_FILE="${ENV_FILE:-$PROJECT_PATH/.env}"
LOG_DIR="${LOG_DIR:-$PROJECT_PATH/logs}"

PID_FILE="${PID_FILE:-$LOG_DIR/benusy.pid}"
LOG_FILE="${LOG_FILE:-$LOG_DIR/benusy.log}"
ACCESS_LOG_FILE="${ACCESS_LOG_FILE:-$LOG_DIR/benusy-access.log}"
HEALTH_PATH="${HEALTH_PATH:-/health}"
SCHEDULER_PID_FILE="${SCHEDULER_PID_FILE:-$LOG_DIR/benusy-scheduler.pid}"
SCHEDULER_LOG_FILE="${SCHEDULER_LOG_FILE:-$LOG_DIR/benusy-scheduler.log}"
SCHEDULER_MODULE="${SCHEDULER_MODULE:-benusy_api.scripts.scheduler_runner}"

HOST="${HOST:-${BIND_HOST:-0.0.0.0}}"
PORT="${PORT:-${UVICORN_PORT:-8100}}"
APP_MODULE="${APP_MODULE:-benusy_api.main:app}"
APP_KEY="${APP_KEY:-${APP_MODULE%%.*}}"
WORKER_CLASS="${WORKER_CLASS:-uvicorn.workers.UvicornWorker}"
TIMEOUT="${TIMEOUT:-120}"
WORKERS="${WORKERS:-}"
SERVER_BACKEND="${SERVER_BACKEND:-}"
UVICORN_LOG_LEVEL="${UVICORN_LOG_LEVEL:-info}"
APP_DIR="${APP_DIR:-src}"

info() { echo "[INFO] $1"; }
warn() { echo "[WARN] $1"; }
error() { echo "[ERROR] $1"; }

if [ ! -d "$API_DIR" ]; then
  error "apps/api directory not found: $API_DIR"
  exit 1
fi

resolve_python_bin() {
  if command -v python3 >/dev/null 2>&1; then
    command -v python3
    return 0
  fi
  command -v python
}

load_env() {
  if [ -f "$ENV_FILE" ]; then
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
  fi
}

ensure_venv() {
  local base_python
  local venv_python="$VENV_DIR/bin/python"
  base_python="$(resolve_python_bin)"

  if [ ! -d "$VENV_DIR" ]; then
    info "Creating virtualenv: $VENV_DIR"
    "$base_python" -m venv "$VENV_DIR"
  fi

  if [ ! -x "$venv_python" ]; then
    warn "Virtualenv is incomplete, recreating: $VENV_DIR"
    rm -rf "$VENV_DIR"
    "$base_python" -m venv "$VENV_DIR"
  fi
}

activate_venv() {
  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"
}

ensure_deps() {
  local venv_python="$VENV_DIR/bin/python"
  if ! (cd "$API_DIR" && PYTHONPATH=src "$venv_python" -c "import benusy_api, fastapi, sqlalchemy, gunicorn" >/dev/null 2>&1); then
    info "Installing/updating dependencies"
    (cd "$API_DIR" && "$venv_python" -m pip install --upgrade pip && "$venv_python" -m pip install -e '.[dev]')
  fi
}

ensure_db_migrated() {
  mkdir -p "$LOG_DIR" "$PROJECT_PATH/data"
  info "Applying DB migrations (alembic upgrade head)"
  (cd "$API_DIR" && PYTHONPATH=src python -m alembic upgrade head)
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

select_server_backend() {
  if [ -n "$SERVER_BACKEND" ]; then
    local normalized
    normalized="$(printf '%s' "$SERVER_BACKEND" | tr '[:upper:]' '[:lower:]')"
    case "$normalized" in
      gunicorn|uvicorn)
        echo "$normalized"
        return
        ;;
      *)
        error "Invalid SERVER_BACKEND: $SERVER_BACKEND (expected gunicorn|uvicorn)"
        exit 1
        ;;
    esac
  fi

  case "$(uname -s 2>/dev/null || true)" in
    Darwin) echo "uvicorn" ;;
    *) echo "gunicorn" ;;
  esac
}

start_with_gunicorn() {
  local workers="$1"
  (
    cd "$API_DIR"
    PYTHONPATH=src "$VENV_DIR/bin/python" -m gunicorn "$APP_MODULE" \
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
}

start_with_uvicorn() {
  (
    cd "$API_DIR"
    PYTHONPATH=src nohup "$VENV_DIR/bin/python" -m uvicorn "$APP_MODULE" \
      --host "$HOST" \
      --port "$PORT" \
      --app-dir "$APP_DIR" \
      --log-level "$UVICORN_LOG_LEVEL" \
      </dev/null >>"$LOG_FILE" 2>&1 &
    echo "$!" >"$PID_FILE"
  )
}

is_running() {
  if [ -f "$PID_FILE" ]; then
    local pid
    pid=$(cat "$PID_FILE" 2>/dev/null || true)
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      return 0
    fi
  fi
  local recovered_pid
  recovered_pid="$(collect_project_port_pids | head -1 || true)"
  if [ -n "$recovered_pid" ]; then
    printf '%s\n' "$recovered_pid" >"$PID_FILE"
    return 0
  fi
  return 1
}

# ─── Scheduler helpers ────────────────────────────────────────────────────────

is_scheduler_running() {
  if [ -f "$SCHEDULER_PID_FILE" ]; then
    local pid
    pid=$(cat "$SCHEDULER_PID_FILE" 2>/dev/null || true)
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      return 0
    fi
  fi
  return 1
}

start_scheduler() {
  if is_scheduler_running; then
    warn "Scheduler already running (PID=$(cat "$SCHEDULER_PID_FILE"))"
    return 0
  fi
  rm -f "$SCHEDULER_PID_FILE"
  : >> "$SCHEDULER_LOG_FILE"
  (
    cd "$API_DIR"
    PYTHONPATH=src nohup "$VENV_DIR/bin/python" -m "$SCHEDULER_MODULE" \
      >>"$SCHEDULER_LOG_FILE" 2>&1 &
    echo "$!" >"$SCHEDULER_PID_FILE"
  )
  sleep 0.5
  if is_scheduler_running; then
    info "Scheduler started (PID=$(cat "$SCHEDULER_PID_FILE"))"
    info "Scheduler log: $SCHEDULER_LOG_FILE"
  else
    warn "Scheduler may have failed to start, check: $SCHEDULER_LOG_FILE"
  fi
}

stop_scheduler() {
  if ! is_scheduler_running; then
    rm -f "$SCHEDULER_PID_FILE"
    return 0
  fi
  local pid
  pid=$(cat "$SCHEDULER_PID_FILE")
  kill "$pid" || true
  local retries=20
  while [ "$retries" -gt 0 ]; do
    if ! kill -0 "$pid" 2>/dev/null; then
      rm -f "$SCHEDULER_PID_FILE"
      info "Scheduler stopped"
      return 0
    fi
    sleep 0.25
    retries=$((retries - 1))
  done
  warn "Scheduler stop timeout, force kill PID=$pid"
  kill -9 "$pid" 2>/dev/null || true
  rm -f "$SCHEDULER_PID_FILE"
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

healthcheck_url() {
  echo "http://127.0.0.1:$PORT$HEALTH_PATH"
}

is_healthy() {
  curl -fsS --max-time 2 "$(healthcheck_url)" >/dev/null 2>&1
}

wait_for_health() {
  local retries=40
  while [ "$retries" -gt 0 ]; do
    if is_running && is_healthy; then
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

  warn "PID file missing/stale, stopping app process(es) on port $PORT: ${owned_pids[*]}"
  kill "${owned_pids[@]}" 2>/dev/null || true

  if wait_for_port_release; then
    info "Stopped listener(s) on port $PORT"
    return 0
  fi

  warn "Graceful stop timed out on port $PORT, force kill: ${owned_pids[*]}"
  kill -9 "${owned_pids[@]}" 2>/dev/null || true

  if wait_for_port_release; then
    info "Stopped listener(s) on port $PORT (forced)"
    return 0
  fi
  return 1
}

force_stop_port_listeners() {
  local pids
  pids="$(list_listening_pids)"
  [ -z "$pids" ] && return 0

  warn "Port $PORT is occupied by other process(es): $pids; terminating them."
  lsof -nP -iTCP:"$PORT" -sTCP:LISTEN || true
  kill $pids 2>/dev/null || true

  if wait_for_port_release; then
    info "Cleared port $PORT"
    return 0
  fi

  warn "Graceful stop timed out on port $PORT, force kill: $pids"
  kill -9 $pids 2>/dev/null || true

  if wait_for_port_release; then
    info "Cleared port $PORT (forced)"
    return 0
  fi

  error "Failed to clear port $PORT"
  lsof -nP -iTCP:"$PORT" -sTCP:LISTEN || true
  exit 1
}

check_port_free() {
  force_stop_port_listeners
}

install_cmd() {
  ensure_venv
  activate_venv
  (cd "$API_DIR" && python -m pip install --upgrade pip && python -m pip install -e '.[dev]')
  info "Dependencies installed"
}

db_upgrade_cmd() {
  load_env
  ensure_venv
  activate_venv
  ensure_deps
  ensure_db_migrated
  info "DB schema is up to date"
}

start() {
  load_env
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
  ensure_db_migrated

  local backend workers
  backend="$(select_server_backend)"
  workers=""
  if [ "$backend" = "gunicorn" ]; then
    workers="$(calc_workers)"
  else
    workers="1"
  fi
  mkdir -p "$LOG_DIR"
  : > "$LOG_FILE"
  : > "$ACCESS_LOG_FILE"

  if [ "$backend" = "uvicorn" ]; then
    warn "Using uvicorn backend on macOS to avoid ObjC fork crash (set SERVER_BACKEND=gunicorn to override)."
  fi
  info "Starting Benusy: $HOST:$PORT mode=$backend workers=$workers"
  if [ "$backend" = "gunicorn" ]; then
    start_with_gunicorn "$workers"
  else
    start_with_uvicorn
  fi

  if wait_for_health; then
    info "Started (PID=$(cat "$PID_FILE"), mode=$backend)"
    info "Log: $LOG_FILE"
    start_scheduler
    return 0
  fi

  error "Failed to start, check log: $LOG_FILE"
  tail -n 40 "$LOG_FILE" || true
  return 1
}

stop() {
  stop_scheduler
  if ! is_running; then
    if stop_port_listeners_if_owned; then
      rm -f "$PID_FILE"
      return 0
    fi
    if [ -n "$(list_listening_pids)" ]; then
      force_stop_port_listeners
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
  if is_running && is_healthy; then
    echo "running pid=$(cat "$PID_FILE") port=$PORT"
  else
    rm -f "$PID_FILE"
    echo "stopped"
  fi
  if is_scheduler_running; then
    echo "scheduler=running pid=$(cat "$SCHEDULER_PID_FILE")"
  else
    rm -f "$SCHEDULER_PID_FILE"
    echo "scheduler=stopped"
  fi
}

restart() {
  stop
  start
}

logs() {
  mkdir -p "$LOG_DIR"
  touch "$LOG_FILE" "$ACCESS_LOG_FILE" "$SCHEDULER_LOG_FILE"
  tail -f "$LOG_FILE" "$ACCESS_LOG_FILE" "$SCHEDULER_LOG_FILE"
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
    error "Current directory is not a git repo, cannot update"
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
  db-upgrade) db_upgrade_cmd ;;
  start) start ;;
  stop) stop ;;
  restart) restart ;;
  status) status ;;
  logs) logs ;;
  ip) ip ;;
  update) update ;;
  *)
    echo "Usage: $0 {install|db-upgrade|start|stop|restart|status|logs|ip|update}"
    exit 1
    ;;
esac

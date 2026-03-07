#!/usr/bin/env bash
set -euo pipefail

PROJECT_PATH="${PROJECT_PATH:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)}"
VENV_DIR="${VENV_DIR:-$PROJECT_PATH/venv}"
ENV_FILE="${ENV_FILE:-$PROJECT_PATH/.env}"
ENV_EXAMPLE_FILE="$PROJECT_PATH/.env.example"
DATA_DIR="${DATA_DIR:-$PROJECT_PATH/data}"
SQLITE_FILE="${SQLITE_FILE:-$DATA_DIR/benfast.sqlite3}"
LEGACY_SQLITE_FILE="$PROJECT_PATH/db.sqlite3"
LOG_DIR="${LOG_DIR:-$PROJECT_PATH/logs}"
PID_FILE="${PID_FILE:-$LOG_DIR/benfast.pid}"
LOG_FILE="${LOG_FILE:-$LOG_DIR/benfast.log}"

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8700}"

info()  { printf '\033[0;32m[INFO]\033[0m  %s\n' "$*"; }
warn()  { printf '\033[0;33m[WARN]\033[0m  %s\n' "$*"; }
error() { printf '\033[0;31m[ERROR]\033[0m %s\n' "$*" >&2; }
die()   { error "$*"; exit 1; }

resolve_python() {
  if command -v python3 >/dev/null 2>&1; then
    command -v python3
    return
  fi
  if command -v python >/dev/null 2>&1; then
    command -v python
    return
  fi
  die "python interpreter not found"
}

PYTHON_BIN="$(resolve_python)"

load_env() {
  if [ -f "$ENV_FILE" ]; then
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
  fi
}

ensure_dirs() {
  mkdir -p "$LOG_DIR" "$DATA_DIR"
}

migrate_legacy_sqlite() {
  local db_engine="${DB_ENGINE:-sqlite}"
  db_engine="$(printf '%s' "$db_engine" | tr '[:upper:]' '[:lower:]')"
  if [ "$db_engine" != "sqlite" ]; then
    return 0
  fi

  if [ -f "$SQLITE_FILE" ]; then
    return 0
  fi

  if [ -f "$LEGACY_SQLITE_FILE" ]; then
    info "Migrating legacy SQLite files to $DATA_DIR"
    mv "$LEGACY_SQLITE_FILE" "$SQLITE_FILE"
    for suffix in "-shm" "-wal" "-journal"; do
      if [ -f "${LEGACY_SQLITE_FILE}${suffix}" ]; then
        mv "${LEGACY_SQLITE_FILE}${suffix}" "${SQLITE_FILE}${suffix}"
      fi
    done
  fi
}

ensure_venv() {
  if [ ! -x "$VENV_DIR/bin/python" ]; then
    info "Creating virtualenv: $VENV_DIR"
    "$PYTHON_BIN" -m venv "$VENV_DIR"
  fi
}

ensure_deps() {
  if ! "$VENV_DIR/bin/python" -c "import fastapi, uvicorn, src" >/dev/null 2>&1; then
    info "Installing dependencies"
    "$VENV_DIR/bin/python" -m pip install -q --upgrade pip
    "$VENV_DIR/bin/python" -m pip install -q -e "$PROJECT_PATH[dev]"
  fi
}

is_running() {
  [ -f "$PID_FILE" ] || return 1
  local pid
  pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null
}

list_listening_pids() {
  lsof -nP -iTCP:"$PORT" -sTCP:LISTEN -t 2>/dev/null | awk '!seen[$0]++'
}

wait_for_port_release() {
  local retries=50
  while [ "$retries" -gt 0 ]; do
    if [ -z "$(list_listening_pids)" ]; then
      return 0
    fi
    sleep 0.2
    retries=$((retries - 1))
  done
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

  pids="$(list_listening_pids)"
  warn "Graceful stop timed out on port $PORT, force kill: $pids"
  [ -n "$pids" ] && kill -9 $pids 2>/dev/null || true

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

wait_for_health() {
  local retries=50
  while [ "$retries" -gt 0 ]; do
    if curl -fsS --max-time 1 "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.2
    retries=$((retries - 1))
  done
  return 1
}

install_cmd() {
  load_env
  ensure_dirs
  migrate_legacy_sqlite
  ensure_venv
  "$VENV_DIR/bin/python" -m pip install -q --upgrade pip
  "$VENV_DIR/bin/python" -m pip install -q -e "$PROJECT_PATH[dev]"
  info "Dependencies installed"
}

init_env_cmd() {
  if [ -f "$ENV_FILE" ]; then
    info ".env already exists: $ENV_FILE"
    return 0
  fi
  if [ ! -f "$ENV_EXAMPLE_FILE" ]; then
    die "Missing env template: $ENV_EXAMPLE_FILE"
  fi
  cp "$ENV_EXAMPLE_FILE" "$ENV_FILE"
  info "Generated .env from template: $ENV_FILE"
}

start_cmd() {
  load_env
  ensure_dirs
  migrate_legacy_sqlite
  ensure_venv
  ensure_deps

  if is_running; then
    info "benfast running pid=$(cat "$PID_FILE") port=$PORT"
    return 0
  fi

  rm -f "$PID_FILE"
  check_port_free
  : > "$LOG_FILE"

  info "Starting Benfast on $HOST:$PORT"
  (
    cd "$PROJECT_PATH"
    nohup env PYTHONPATH=src "$VENV_DIR/bin/python" -m uvicorn src:app \
      --host "$HOST" --port "$PORT" >>"$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
  )

  if wait_for_health; then
    info "benfast running pid=$(cat "$PID_FILE") port=$PORT"
    return 0
  fi

  error "Failed to start Benfast; check log: $LOG_FILE"
  [ -f "$LOG_FILE" ] && tail -n 40 "$LOG_FILE" >&2 || true
  return 1
}

stop_cmd() {
  if ! is_running; then
    if [ -n "$(list_listening_pids)" ]; then
      force_stop_port_listeners
    fi
    rm -f "$PID_FILE"
    info "benfast stopped port=$PORT"
    return 0
  fi

  local pid
  pid="$(cat "$PID_FILE")"
  kill "$pid" 2>/dev/null || true
  sleep 0.6
  if kill -0 "$pid" 2>/dev/null; then
    kill -9 "$pid" 2>/dev/null || true
  fi
  rm -f "$PID_FILE"
  [ -n "$(list_listening_pids)" ] && force_stop_port_listeners
  info "benfast stopped port=$PORT"
}

status_cmd() {
  load_env
  if is_running; then
    echo "running pid=$(cat "$PID_FILE") port=$PORT"
  else
    [ -f "$PID_FILE" ] && rm -f "$PID_FILE"
    echo "stopped port=$PORT"
  fi
}

logs_cmd() {
  ensure_dirs
  touch "$LOG_FILE"
  tail -f "$LOG_FILE"
}

ip_cmd() {
  echo "http://localhost:$PORT"
}

check_cmd() {
  load_env
  ensure_dirs
  migrate_legacy_sqlite
  ensure_venv
  ensure_deps
  (cd "$PROJECT_PATH" && "$VENV_DIR/bin/python" -m compileall -q src)
  info "Compile check passed"
}

test_cmd() {
  load_env
  ensure_dirs
  migrate_legacy_sqlite
  ensure_venv
  ensure_deps
  (
    cd "$PROJECT_PATH"
    TESTING=true APP_ENV=testing SWAGGER_UI_PASSWORD=test_password \
      "$VENV_DIR/bin/python" -m pytest -q
  )
}

update_cmd() {
  install_cmd
}

case "${1:-}" in
  install) install_cmd ;;
  init-env) init_env_cmd ;;
  start) start_cmd ;;
  stop) stop_cmd ;;
  restart) stop_cmd; start_cmd ;;
  status) status_cmd ;;
  logs) logs_cmd ;;
  ip) ip_cmd ;;
  check) check_cmd ;;
  test) test_cmd ;;
  update) update_cmd ;;
  *)
    echo "Usage: $0 {install|init-env|start|stop|restart|status|logs|ip|check|test|update}"
    exit 1
    ;;
esac

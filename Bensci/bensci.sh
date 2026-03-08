#!/usr/bin/env bash
# CATAPEDIA Metadata Service Startup Script

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
cd "$SCRIPT_DIR"
API_DIR="$SCRIPT_DIR/apps/api"

if [ -z "${VENV_DIR:-}" ]; then
    if [ -x "$SCRIPT_DIR/venv/bin/python" ]; then
        VENV_DIR="$SCRIPT_DIR/venv"
    elif [ -x "$SCRIPT_DIR/.venv/bin/python" ]; then
        VENV_DIR="$SCRIPT_DIR/.venv"
    else
        VENV_DIR="$SCRIPT_DIR/venv"
    fi
fi

resolve_python() {
    if command -v python3 >/dev/null 2>&1; then
        command -v python3
        return 0
    fi
    command -v python
}

PYTHON_BIN="$(resolve_python)"

load_env() {
    [ -f "$SCRIPT_DIR/.env" ] || return 0

    while IFS= read -r raw_line || [ -n "$raw_line" ]; do
        local line key value
        line="${raw_line#"${raw_line%%[![:space:]]*}"}"
        case "$line" in
            ""|\#*) continue ;;
        esac
        [[ "$line" == *=* ]] || continue

        key="${line%%=*}"
        value="${line#*=}"
        key="${key%"${key##*[![:space:]]}"}"
        value="${value#"${value%%[![:space:]]*}"}"
        value="${value%"${value##*[![:space:]]}"}"

        if [ "${#value}" -ge 2 ]; then
            case "$value" in
                \"*\"|\'*\')
                    value="${value:1:${#value}-2}"
                    ;;
            esac
        fi

        export "$key=$value"
    done < "$SCRIPT_DIR/.env"
}

# Default values
PORT=${PORT:-8300}
HOST=${HOST:-0.0.0.0}
WORKERS=${WORKERS:-4}

# PID and log files
PID_FILE="$SCRIPT_DIR/logs/metadata_service.pid"
LOG_FILE="$SCRIPT_DIR/logs/metadata_service.log"
ACCESS_LOG_FILE="$SCRIPT_DIR/logs/metadata_service_access.log"

# Ensure runtime directories exist
mkdir -p "$SCRIPT_DIR/logs" "$SCRIPT_DIR/data" "$SCRIPT_DIR/data/exports"

ensure_venv() {
    if [ ! -x "$VENV_DIR/bin/python" ]; then
        echo "[INFO] Creating virtualenv: $VENV_DIR"
        "$PYTHON_BIN" -m venv "$VENV_DIR"
    fi
}

ensure_deps() {
    if ! (cd "$SCRIPT_DIR" && PYTHONPATH=. "$VENV_DIR/bin/python" -c "import fastapi, gunicorn, apps.main" >/dev/null 2>&1); then
        echo "[INFO] Installing/updating dependencies"
        (
            cd "$API_DIR"
            "$VENV_DIR/bin/python" -m pip install -q --upgrade pip
            "$VENV_DIR/bin/python" -m pip install -q -e ".[dev]"
        )
    fi
}

list_listening_pids() {
    lsof -nP -iTCP:"$PORT" -sTCP:LISTEN -t 2>/dev/null | awk '!seen[$0]++' || true
}

wait_for_port_release() {
    local retries=60
    while [ "$retries" -gt 0 ]; do
        if [ -z "$(list_listening_pids)" ]; then
            return 0
        fi
        sleep 0.5
        retries=$((retries - 1))
    done
    return 1
}

force_stop_port_listeners() {
    local pids
    pids="$(list_listening_pids)"
    [ -z "$pids" ] && return 0

    echo "[WARN] Port $PORT is occupied by process(es): $pids; terminating them."
    lsof -nP -iTCP:"$PORT" -sTCP:LISTEN || true
    kill $pids 2>/dev/null || true

    if wait_for_port_release; then
        echo "[INFO] Cleared port $PORT"
        return 0
    fi

    pids="$(list_listening_pids)"
    echo "[WARN] Graceful stop timed out on port $PORT, force kill: $pids"
    [ -n "$pids" ] && kill -9 $pids 2>/dev/null || true

    if wait_for_port_release; then
        echo "[INFO] Cleared port $PORT (forced)"
        return 0
    fi

    echo "[ERROR] Failed to clear port $PORT"
    lsof -nP -iTCP:"$PORT" -sTCP:LISTEN || true
    exit 1
}

wait_for_health() {
    local retries=60
    while [ "$retries" -gt 0 ]; do
        if is_running && curl -fsS --max-time 2 "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
            return 0
        fi
        sleep 0.5
        retries=$((retries - 1))
    done
    return 1
}

# Function to check if service is running
is_running() {
    if [ -f "$PID_FILE" ]; then
        local pid
        pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        fi
    fi
    return 1
}

# Function to start the service
start() {
    load_env
    ensure_venv
    ensure_deps

    if is_running; then
        echo "[WARN] Service is already running (PID=$(cat $PID_FILE))"
        exit 1
    fi

    force_stop_port_listeners

    echo "[INFO] Starting CATAPEDIA Metadata Service on $HOST:$PORT with $WORKERS workers..."

    # Start gunicorn with uvicorn workers
    "$VENV_DIR/bin/python" -m gunicorn apps.main:app \
        --bind $HOST:$PORT \
        --workers $WORKERS \
        --worker-class uvicorn.workers.UvicornWorker \
        --timeout 120 \
        --pid $PID_FILE \
        --daemon \
        --log-file $LOG_FILE \
        --access-logfile $ACCESS_LOG_FILE \
        --capture-output

    if wait_for_health; then
        echo "[OK] Service started successfully (PID=$(cat $PID_FILE))"
        echo "[INFO] Logs: $LOG_FILE"
        echo "[INFO] Access logs: $ACCESS_LOG_FILE"
    else
        echo "[ERROR] Failed to start service"
        [ -f "$LOG_FILE" ] && tail -n 40 "$LOG_FILE"
        exit 1
    fi
}

# Function to stop the service
stop() {
    if is_running; then
        PID=$(cat "$PID_FILE")
        echo "[INFO] Stopping service (PID=$PID)..."
        kill $PID
        sleep 2
        
        # Force kill if still running
        if ps -p $PID > /dev/null 2>&1; then
            kill -9 $PID
        fi
        
        rm -f "$PID_FILE"
        echo "[OK] Service stopped"
    else
        force_stop_port_listeners
        echo "[INFO] Service is not running"
    fi
}

# Function to restart the service
restart() {
    stop
    sleep 2
    start
}

# Function to show status
status() {
    if is_running; then
        PID=$(cat "$PID_FILE")
        echo "[OK] Service is running (PID=$PID)"
        echo "[INFO] Bound to: $HOST:$PORT"
        
        # Show memory usage
        if command -v ps &> /dev/null; then
            MEM=$(ps -o rss= -p $PID 2>/dev/null || echo "N/A")
            echo "[INFO] Memory: $((MEM / 1024)) MB"
        fi
    else
        echo "[INFO] Service is not running"
    fi
}

# Function to show logs
logs() {
    if [ -f "$LOG_FILE" ]; then
        tail -f "$LOG_FILE"
    else
        echo "[ERROR] Log file not found: $LOG_FILE"
        exit 1
    fi
}

# Main command handler
case "${1:-start}" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    logs)
        logs
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs}"
        echo ""
        echo "Commands:"
        echo "  start   - Start the service"
        echo "  stop    - Stop the service"
        echo "  restart - Restart the service"
        echo "  status  - Show service status"
        echo "  logs    - Show service logs (tail -f)"
        exit 1
        ;;
esac

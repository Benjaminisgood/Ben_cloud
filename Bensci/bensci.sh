#!/bin/bash
# CATAPEDIA Metadata Service Startup Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load environment variables
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

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

# Function to check if service is running
is_running() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            return 0
        fi
    fi
    return 1
}

# Function to start the service
start() {
    if is_running; then
        echo "[WARN] Service is already running (PID=$(cat $PID_FILE))"
        exit 1
    fi

    echo "[INFO] Starting CATAPEDIA Metadata Service on $HOST:$PORT with $WORKERS workers..."
    
    # Activate virtual environment if exists
    if [ -d "$SCRIPT_DIR/venv" ]; then
        source "$SCRIPT_DIR/venv/bin/activate"
    fi
    
    # Start gunicorn with uvicorn workers
    nohup python -m gunicorn apps.main:app \
        --bind $HOST:$PORT \
        --workers $WORKERS \
        --worker-class uvicorn.workers.UvicornWorker \
        --timeout 120 \
        --pid $PID_FILE \
        --daemon \
        --log-file $LOG_FILE \
        --access-logfile $ACCESS_LOG_FILE \
        --capture-output \
        2>&1
    
    sleep 2
    
    if is_running; then
        echo "[OK] Service started successfully (PID=$(cat $PID_FILE))"
        echo "[INFO] Logs: $LOG_FILE"
        echo "[INFO] Access logs: $ACCESS_LOG_FILE"
    else
        echo "[ERROR] Failed to start service"
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

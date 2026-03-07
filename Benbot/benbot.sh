#!/usr/bin/env bash
# Benbot 服务管理脚本（与 benlab.sh / benoss.sh 接口一致）
# 用法: ./benbot.sh {install|start|stop|restart|status|logs|ip|init-env|update}
set -euo pipefail

PROJECT_PATH="${PROJECT_PATH:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)}"
API_DIR="$PROJECT_PATH/apps/api"
VENV_DIR="${VENV_DIR:-$PROJECT_PATH/venv}"
ENV_FILE="${ENV_FILE:-$PROJECT_PATH/.env}"
ENV_EXAMPLE_FILE="${ENV_EXAMPLE_FILE:-$PROJECT_PATH/.env.example}"
LOG_DIR="${LOG_DIR:-$PROJECT_PATH/logs}"

PID_FILE="$LOG_DIR/benbot.pid"
LOG_FILE="$LOG_DIR/benbot.log"
ACCESS_LOG_FILE="$LOG_DIR/benbot-access.log"

HOST="${HOST:-0.0.0.0}"
APP_MODULE="${APP_MODULE:-benbot_api.main:app}"
APP_KEY="${APP_KEY:-${APP_MODULE%%.*}}"
WORKER_CLASS="${WORKER_CLASS:-uvicorn.workers.UvicornWorker}"
TIMEOUT="${TIMEOUT:-120}"
WORKERS="${WORKERS:-}"
SERVER_BACKEND="${SERVER_BACKEND:-}"          # gunicorn | uvicorn | (自动)
UVICORN_LOG_LEVEL="${UVICORN_LOG_LEVEL:-info}"

info()  { printf '\033[0;32m[INFO]\033[0m  %s\n' "$*"; }
warn()  { printf '\033[0;33m[WARN]\033[0m  %s\n' "$*"; }
error() { printf '\033[0;31m[ERROR]\033[0m %s\n' "$*" >&2; }
die()   { error "$*"; exit 1; }

has_cmd() {
  command -v "$1" >/dev/null 2>&1
}

# ─── 读取 .env 中单个 KEY 的值 ────────────────────────────────────────────────
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

_get_port() {
  local p
  p="$(_read_env_key "$ENV_FILE" PORT)"
  echo "${p:-80}"     # 统一端口 80（生产/开发一致）
}

PORT="${PORT:-$(_get_port)}"

# ─── Env / Venv ───────────────────────────────────────────────────────────────
load_env() {
  [ -f "$ENV_FILE" ] || return 0
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
  # 重新读取 PORT（source 可能更新了它）
  local p; p="$(_read_env_key "$ENV_FILE" PORT)"; PORT="${p:-$PORT}"
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
  if ! (cd "$API_DIR" && PYTHONPATH=src python -c \
        "import benbot_api, fastapi, sqlalchemy, gunicorn" >/dev/null 2>&1); then
    info "安装/更新依赖"
    (cd "$API_DIR" && python -m pip install -q --upgrade pip \
                           && python -m pip install -q -e '.[dev]')
  fi
}

calc_workers() {
  [ -n "$WORKERS" ] && echo "$WORKERS" && return
  python3 - <<'PY'
import multiprocessing
print(max(2, min(4, multiprocessing.cpu_count() + 1)))
PY
}

# ─── 进程 / 端口工具 ──────────────────────────────────────────────────────────
is_running() {
  [ -f "$PID_FILE" ] || return 1
  local pid
  pid=$(cat "$PID_FILE" 2>/dev/null || true)
  [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null
}

_port_pids_for_port() {
  local port="$1"

  # 优先 lsof；若未安装则回退 ss/netstat（最常见于精简 Linux 镜像）
  if has_cmd lsof; then
    lsof -nP -iTCP:"$port" -sTCP:LISTEN -t 2>/dev/null | awk '!seen[$0]++' || true
    return 0
  fi

  if has_cmd ss; then
    ss -ltnp 2>/dev/null | awk -v port="$port" '
      $1=="LISTEN" && ($4 ~ (":" port "$") || $4 ~ ("\\]:" port "$")) {
        line=$0
        while (match(line, /pid=[0-9]+/)) {
          pid=substr(line, RSTART + 4, RLENGTH - 4)
          if (pid ~ /^[0-9]+$/) print pid
          line=substr(line, RSTART + RLENGTH)
        }
      }
    ' | awk '!seen[$0]++' || true
    return 0
  fi

  if has_cmd netstat; then
    netstat -lntp 2>/dev/null | awk -v port="$port" '
      ($4 ~ (":" port "$") || $4 ~ ("\\]:" port "$")) {
        split($7, a, "/")
        if (a[1] ~ /^[0-9]+$/) print a[1]
      }
    ' | awk '!seen[$0]++' || true
    return 0
  fi

  # 无可用端口探测工具时，返回空并由后续启动探活兜底
  return 0
}

_port_pids() {
  _port_pids_for_port "$PORT"
}

_pid_parent() {
  ps -o ppid= -p "$1" 2>/dev/null | tr -d '[:space:]' || true
}

_is_descendant_of() {
  local pid="$1" ancestor="$2"
  case "$pid" in ''|*[!0-9]*) return 1 ;; esac
  case "$ancestor" in ''|*[!0-9]*) return 1 ;; esac

  while [ "$pid" -gt 1 ] 2>/dev/null; do
    [ "$pid" = "$ancestor" ] && return 0
    pid="$(_pid_parent "$pid")"
    case "$pid" in ''|*[!0-9]*) break ;; esac
  done
  return 1
}

_listener_has_our_process() {
  local owner_pid="$1" pid pids
  pids="$(_port_pids)"
  [ -z "$pids" ] && return 1
  for pid in $pids; do
    [ "$pid" = "$owner_pid" ] && return 0
    _is_descendant_of "$pid" "$owner_pid" && return 0
    _is_our_pid "$pid" && return 0
  done
  return 1
}

_health_ready() {
  local url="http://127.0.0.1:$PORT/health"
  if has_cmd curl; then
    curl -fsS --max-time 2 "$url" 2>/dev/null | grep -q '"status"[[:space:]]*:[[:space:]]*"ok"'
    return $?
  fi
  python - "$url" <<'PY'
import json
import sys
import urllib.request

url = sys.argv[1]
try:
    with urllib.request.urlopen(url, timeout=2) as resp:
        payload = json.loads(resp.read().decode("utf-8", "replace"))
    if payload.get("status") == "ok":
        raise SystemExit(0)
except Exception:
    pass
raise SystemExit(1)
PY
}

wait_for_startup() {
  local retries=40 pid
  while [ "$retries" -gt 0 ]; do
    if is_running; then
      pid=$(cat "$PID_FILE" 2>/dev/null || true)
      if [ -n "$pid" ] && _listener_has_our_process "$pid"; then
        return 0
      fi
      # 当端口探测不可用或输出受限时，退化为 /health 探活
      _health_ready && return 0
    fi
    sleep 0.25; retries=$((retries - 1))
  done
  return 1
}

_is_our_pid() {
  local pid="$1"
  local cmd; cmd="$(ps -o command= -p "$pid" 2>/dev/null || true)"
  case "$cmd" in
    *"$PROJECT_PATH"*|*"$APP_MODULE"*|*"$APP_KEY"*) return 0 ;;
  esac
  return 1
}

ensure_port_free() {
  if ! has_cmd lsof && ! has_cmd ss && ! has_cmd netstat; then
    warn "未安装 lsof/ss/netstat，跳过启动前端口占用预检，将在启动后做探活校验"
    return 0
  fi

  local pids
  pids="$(_port_pids)"
  [ -z "$pids" ] && return 0   # ✓ 端口空闲

  warn "端口 $PORT 被进程占用 ($pids)，正在终止..."
  lsof -nP -iTCP:"$PORT" -sTCP:LISTEN || true
  kill $pids 2>/dev/null || true
  sleep 0.5

  pids="$(_port_pids)"
  if [ -z "$pids" ]; then
    info "端口 $PORT 已释放"
    return 0
  fi

  warn "优雅停止超时，强制终止端口 $PORT 进程: $pids"
  kill -9 $pids 2>/dev/null || true
  sleep 0.5

  pids="$(_port_pids)"
  if [ -z "$pids" ]; then
    info "端口 $PORT 已强制释放"
    return 0
  fi

  die "无法释放端口 $PORT"
}

# ─── 后端选择（macOS 用 uvicorn 规避 ObjC fork crash）────────────────────────
select_server_backend() {
  if [ -n "$SERVER_BACKEND" ]; then
    local norm
    norm="$(printf '%s' "$SERVER_BACKEND" | tr '[:upper:]' '[:lower:]')"
    case "$norm" in
      gunicorn|uvicorn) echo "$norm"; return ;;
      *) die "SERVER_BACKEND 无效: $SERVER_BACKEND（允许值: gunicorn|uvicorn）" ;;
    esac
  fi
  case "$(uname -s 2>/dev/null || true)" in
    Darwin) echo "uvicorn" ;;
    *)      echo "gunicorn" ;;
  esac
}

start_with_gunicorn() {
  local workers="$1"
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
}

start_with_uvicorn() {
  (
    cd "$API_DIR"
    PYTHONPATH=src nohup python -m uvicorn "$APP_MODULE" \
      --host "$HOST" \
      --port "$PORT" \
      --app-dir src \
      --log-level "$UVICORN_LOG_LEVEL" \
      >>"$LOG_FILE" 2>&1 &
    echo "$!" >"$PID_FILE"
  )
}

# ─── 命令实现 ──────────────────────────────────────────────────────────────────
install_cmd() {
  ensure_venv; activate_venv
  (cd "$API_DIR" && python -m pip install -q --upgrade pip \
                        && python -m pip install -q -e '.[dev]')
  info "依赖安装完成"
}

start() {
  load_env
  ensure_venv; activate_venv; ensure_deps

  if is_running; then
    warn "服务已运行 (PID=$(cat "$PID_FILE"), port=$PORT)"
    return 0
  fi

  rm -f "$PID_FILE"
  ensure_port_free   # ← 自动解决端口冲突

  local backend workers
  backend="$(select_server_backend)"
  if [ "$backend" = "gunicorn" ]; then
    workers="$(calc_workers)"
  else
    workers="1"
  fi

  mkdir -p "$LOG_DIR"
  : > "$LOG_FILE"; : > "$ACCESS_LOG_FILE"

  # 在 gunicorn 多 worker 启动前，单进程完成 DB 初始化和管理员播种
  # 避免多 worker 并发竞争 SQLite 写锁，也确保 worker 崩溃时不丢失初始化
  info "初始化数据库及管理员账号..."
  if ! (cd "$API_DIR" && PYTHONPATH=src python -c "
import logging, sys
logging.basicConfig(level=logging.INFO, format='%(levelname)s %(name)s - %(message)s', stream=sys.stdout)
from benbot_api.db.session import init_db
init_db()
" 2>&1 | tee -a "$LOG_FILE"); then
    warn "数据库初始化遇到问题，请检查 $LOG_FILE"
  fi

  if [ "$backend" = "uvicorn" ]; then
    warn "macOS 检测到：使用 uvicorn 后端以规避 ObjC fork crash（设置 SERVER_BACKEND=gunicorn 可强制使用 gunicorn）"
  fi
  info "启动 Benbot: $HOST:$PORT  backend=$backend workers=$workers"

  if [ "$backend" = "gunicorn" ]; then
    start_with_gunicorn "$workers"
  else
    start_with_uvicorn
  fi

  if wait_for_startup; then
    info "启动成功 (PID=$(cat "$PID_FILE"))"
    info "访问: http://localhost:$PORT"
    info "日志: $LOG_FILE"
    return 0
  fi

  error "启动失败，请检查日志: $LOG_FILE"
  tail -20 "$LOG_FILE" >&2 || true
  return 1
}

stop() {
  load_env

  if is_running; then
    local pid; pid=$(cat "$PID_FILE")
    kill "$pid" 2>/dev/null || true
    info "正在停止 (PID=$pid)..."
    local retries=40
    while [ "$retries" -gt 0 ]; do
      kill -0 "$pid" 2>/dev/null || { rm -f "$PID_FILE"; info "已停止"; return 0; }
      sleep 0.25; retries=$((retries - 1))
    done
    warn "优雅停止超时，强制终止 PID=$pid"
    kill -9 "$pid" 2>/dev/null || true
    rm -f "$PID_FILE"
    info "已强制停止"
    return 0
  fi

  rm -f "$PID_FILE"

  # PID 文件不存在时，也直接清理该端口上的占用进程
  local pids; pids="$(_port_pids)"
  if [ -n "$pids" ]; then
    ensure_port_free
    return 0
  fi

  warn "服务未运行"
  return 0
}

status() {
  load_env
  if is_running; then
    echo "running pid=$(cat "$PID_FILE") port=$PORT"
  else
    echo "stopped port=$PORT"
  fi
}

restart() { stop; start; }

logs() {
  mkdir -p "$LOG_DIR"
  touch "$LOG_FILE" "$ACCESS_LOG_FILE"
  tail -f "$LOG_FILE" "$ACCESS_LOG_FILE"
}

ip() {
  load_env
  echo "http://localhost:$PORT"
  local lan_ip
  lan_ip=$(ifconfig 2>/dev/null | awk '/inet / && $2!="127.0.0.1"{print $2; exit}' || true)
  [ -n "$lan_ip" ] && echo "http://$lan_ip:$PORT"
}

update() {
  local was_running=0
  is_running && was_running=1 && stop
  install_cmd
  [ "$was_running" -eq 1 ] && start
}

init_env() {
  if [ -f "$ENV_FILE" ]; then
    info ".env 已存在：$ENV_FILE"
    return 0
  fi
  [ -f "$ENV_EXAMPLE_FILE" ] || die "未找到模板文件：$ENV_EXAMPLE_FILE"
  cp "$ENV_EXAMPLE_FILE" "$ENV_FILE"
  info "已生成配置文件：$ENV_FILE"
  warn "请先按实际环境补全 .env 中的密钥与 URL 配置"
}

case "${1:-}" in
  install)  install_cmd ;;
  start)    start ;;
  stop)     stop ;;
  restart)  restart ;;
  status)   status ;;
  logs)     logs ;;
  ip)       ip ;;
  init-env) init_env ;;
  update)   update ;;
  *)
    echo "用法: $0 {install|start|stop|restart|status|logs|ip|init-env|update}"
    exit 1
    ;;
esac

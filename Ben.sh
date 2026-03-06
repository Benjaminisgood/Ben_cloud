#!/usr/bin/env bash
# ==============================================================================
# Ben.sh — Ben_cloud 统一启动入口
#
# 职责：自动发现根目录内所有子项目并统一调度，不做任何其他事情。
#
# 子项目发现规则：
#   <根目录>/<DirName>/<dirname>.sh 存在（名称小写对应）即视为合法子项目。
#   示例：Benbot/benbot.sh  Benoss/benoss.sh  Benlab/benlab.sh
#   Benbot 作为门户始终最后启动；start all 完成后自动在浏览器打开入口页。
#
# 用法：
#   ./Ben.sh start   [all|<app>]   启动（all 时最后自动打开 Benbot 门户）
#   ./Ben.sh stop    [all|<app>]
#   ./Ben.sh restart [all|<app>]
#   ./Ben.sh status  [all|<app>]   彩色表格展示各服务状态
#   ./Ben.sh install [all|<app>]
#   ./Ben.sh update  [all|<app>]
#   ./Ben.sh logs    <app>         跟踪日志（需指定单个 app）
#   ./Ben.sh ip      <app>         查看访问地址
#   ./Ben.sh open                  直接在浏览器打开 Benbot 门户
#   ./Ben.sh help
# ==============================================================================
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"

# ─── 日志 ──────────────────────────────────────────────────────────────────────
info()  { printf '\033[0;32m[INFO]\033[0m  %s\n' "$*"; }
warn()  { printf '\033[0;33m[WARN]\033[0m  %s\n' "$*"; }
error() { printf '\033[0;31m[ERROR]\033[0m %s\n' "$*" >&2; }
die()   { error "$*"; exit 1; }

usage() {
  cat <<'EOF'
Usage: ./Ben.sh <command> [app]

  start   [all|<app>]   启动服务（all 时最后自动打开 Benbot 门户）
  stop    [all|<app>]
  restart [all|<app>]
  status  [all|<app>]   彩色表格展示各服务状态
  install [all|<app>]
  update  [all|<app>]
  logs    <app>         跟踪日志（需指定单个 app）
  ip      <app>         查看访问地址
  open                  在浏览器打开 Benbot 门户
  help
EOF
}

# ─── 转小写（兼容 macOS 系统默认的 bash 3.x）─────────────────────────────────
_lower() { printf '%s' "$1" | tr '[:upper:]' '[:lower:]'; }

# ─── 读取某 .env 文件中指定 KEY 的值 ──────────────────────────────────────────
_env_key() {
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

# ─── 子项目自动发现 ─────────────────────────────────────────────────────────────
# 返回：非 benbot 项目（字母序）在前，benbot 在最后
_discover_apps() {
  local dir name id script non_portal="" portal=""
  for dir in "$ROOT_DIR"/*/; do
    [ -d "$dir" ] || continue
    name="$(basename "$dir")"
    id="$(_lower "$name")"
    script="${dir}${id}.sh"
    [ -f "$script" ] || continue
    if [ "$id" = "benbot" ]; then
      portal="$id"
    else
      non_portal="$non_portal $id"
    fi
  done
  local sorted=""
  [ -n "$non_portal" ] && sorted="$(printf '%s\n' $non_portal | sort | tr '\n' ' ')"
  printf '%s' "${sorted}${portal}"
}

# 返回 app 对应的 .sh 脚本完整路径；找不到时 error+return 1（不 exit，让调用方决定）
_app_script() {
  local id="$1" dir name
  for dir in "$ROOT_DIR"/*/; do
    [ -d "$dir" ] || continue
    name="$(basename "$dir")"
    if [ "$(_lower "$name")" = "$id" ]; then
      local script="${dir}${id}.sh"
      [ -f "$script" ] && echo "$script" && return 0
    fi
  done
  error "找不到项目 '$id' 的启动脚本（期望 <Dir>/${id}.sh）"
  return 1
}

# 读取 app 的端口号（从其 .env 中的 PORT 字段）
_app_port() {
  local id="$1" dir name
  for dir in "$ROOT_DIR"/*/; do
    [ -d "$dir" ] || continue
    name="$(basename "$dir")"
    if [ "$(_lower "$name")" = "$id" ]; then
      _env_key "${dir}.env" PORT
      return 0
    fi
  done
}

APPS="$(_discover_apps)"   # 空格分隔的已发现项目列表

_normalize() {
  local t="${1:-all}"
  [ "$t" = "all" ] && echo "all" && return
  local a
  for a in $APPS; do [ "$a" = "$t" ] && echo "$t" && return; done
  die "未知项目: $t  （可用: all | $(printf '%s' "$APPS" | tr ' ' '|')）"
}

# ─── 核心调度：调用子项目脚本 ─────────────────────────────────────────────────
_run_one() {
  local app="$1" action="$2"
  local script
  # 先解析路径；_app_script 失败时 return 1，避免 bash "" 报神秘错误
  script="$(_app_script "$app")" || return 1
  bash "$script" "$action"
}

# _run_all 遇到单个失败时继续执行其余 app，最终汇报整体结果
_run_all() {
  local action="$1" _failed=0
  local app
  for app in $APPS; do
    info "[$app] $action"
    _run_one "$app" "$action" || { warn "[$app] $action 失败，继续执行其他项目..."; _failed=1; }
  done
  return $_failed
}

# ─── status 彩色表格 ───────────────────────────────────────────────────────────
cmd_status() {
  local show_apps="${1:-$APPS}"
  printf '\n\033[1m%-12s %-10s %-7s %s\033[0m\n' "PROJECT" "STATUS" "PORT" "PID"
  printf '%s\n' "─────────────────────────────────────────"
  local app out state pid port col
  for app in $show_apps; do
    out="$(_run_one "$app" status 2>&1 || true)"
    state="$(printf '%s' "$out" | grep -o 'running\|stopped' | head -1 || true)"
    pid="$(  printf '%s' "$out" | grep -o 'pid=[0-9]*'       | head -1 | cut -d= -f2 || true)"
    port="$( printf '%s' "$out" | grep -o 'port=[0-9]*'      | head -1 | cut -d= -f2 || true)"
    [ -z "$port" ] && port="$(_app_port "$app")"
    case "${state:-}" in
      running) col="\033[0;32mrunning  \033[0m" ;;
      stopped) col="\033[0;31mstopped  \033[0m" ;;
      *)       col="\033[0;33munknown  \033[0m" ;;
    esac
    printf '%-12s %b %-7s %s\n' "$app" "$col" "${port:--}" "${pid:--}"
  done
  printf '\n'
}

# ─── 打开 Benbot 门户 ─────────────────────────────────────────────────────────
cmd_open() {
  local port; port="$(_app_port "benbot")"; port="${port:-80}"
  local url="http://localhost:$port"
  info "打开 Benbot 门户: $url"
  if   command -v open     >/dev/null 2>&1; then open "$url"
  elif command -v xdg-open >/dev/null 2>&1; then xdg-open "$url" &
  else warn "请手动访问: $url"
  fi
}

# ─── Main ──────────────────────────────────────────────────────────────────────
main() {
  local cmd="${1:-help}"; shift || true

  case "$cmd" in
    start)
      local t; t="$(_normalize "${1:-all}")"
      if [ "$t" = "all" ]; then
        _run_all start
        # Benbot 已在 all 里启动；稍等后打开门户
        printf '%s' "$APPS" | grep -qw benbot && { sleep 1; cmd_open; }
      else
        _run_one "$t" start
        # 单独启动 benbot 时也打开门户
        [ "$t" = "benbot" ] && { sleep 1; cmd_open; }
      fi
      ;;

    stop|restart|install|update)
      local t; t="$(_normalize "${1:-all}")"
      # 用 if/else 而非 A&&B||C，避免 B 失败时 C 以错误参数运行
      if [ "$t" = "all" ]; then _run_all "$cmd"; else _run_one "$t" "$cmd"; fi
      ;;

    status)
      local t; t="$(_normalize "${1:-all}")"
      if [ "$t" = "all" ]; then cmd_status "$APPS"; else cmd_status "$t"; fi
      ;;

    logs|ip)
      [ "${1:-}" ] || die "'$cmd' 需要指定 app（例: ./Ben.sh $cmd benoss）"
      _run_one "$(_normalize "$1")" "$cmd"
      ;;

    open)   cmd_open ;;
    help|--help|-h) usage ;;
    *)
      error "未知命令: $cmd"
      usage; exit 1
      ;;
  esac
}

main "$@"

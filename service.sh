#!/bin/bash
# Kimi2Moon 服务管理脚本 (无 launchctl 版本)

set -uo pipefail

LABEL="com.kimi2moon.service"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$PROJECT_DIR/.service.pid"
LOG_DIR="$PROJECT_DIR/logs"
OUT_LOG="$LOG_DIR/service.out.log"
ERR_LOG="$LOG_DIR/service.err.log"

# 可通过环境变量覆盖
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
DEFAULT_MODEL="${DEFAULT_MODEL:-kimi/k2.5}"
DEBUG="${DEBUG:-false}"

print_help() {
    cat <<EOF
用法: ./service.sh <command>

命令:
  start       启动服务（后台运行）
  stop        停止服务
  restart     重启服务
  status      查看服务状态
  logs        查看服务日志（持续输出）
  run         前台运行（调试模式）

可选环境变量:
  HOST, PORT, DEFAULT_MODEL, DEBUG
EOF
}

ensure_dirs() {
    mkdir -p "$LOG_DIR"
}

resolve_python() {
    if [[ -x "$PROJECT_DIR/venv/bin/python3" ]]; then
        echo "$PROJECT_DIR/venv/bin/python3"
        return
    fi
    if [[ -x "$PROJECT_DIR/.venv/bin/python3" ]]; then
        echo "$PROJECT_DIR/.venv/bin/python3"
        return
    fi
    command -v python3
}

ensure_deps() {
    local python_bin
    python_bin="$(resolve_python)"
    if ! "$python_bin" -c "import fastapi" >/dev/null 2>&1; then
        echo "安装依赖中..."
        "$python_bin" -m pip install -r "$PROJECT_DIR/requirements.txt"
    fi
}

is_running() {
    if [[ -f "$PID_FILE" ]]; then
        local pid
        pid=$(cat "$PID_FILE" 2>/dev/null)
        if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
            return 0
        fi
    fi
    return 1
}

get_pid() {
    cat "$PID_FILE" 2>/dev/null || echo ""
}

get_pid_by_port() {
    # 通过端口查找进程 PID
    local pid=""
    if command -v lsof &>/dev/null; then
        pid=$(lsof -ti tcp:"$PORT" 2>/dev/null | head -n1)
    elif command -v ss &>/dev/null; then
        pid=$(ss -ltnp "sport = :$PORT" 2>/dev/null | grep -oP 'pid=\K[0-9]+' | head -n1)
    elif command -v netstat &>/dev/null; then
        pid=$(netstat -ltnp 2>/dev/null | grep ":$PORT " | awk '{print $7}' | cut -d'/' -f1 | head -n1)
    fi
    echo "$pid"
}

cmd_start() {
    ensure_deps
    ensure_dirs
    
    if is_running; then
        echo "服务已在运行中 (PID: $(get_pid))"
        return 0
    fi
    
    echo "正在启动 Kimi2Moon 服务..."
    
    # 清空旧日志
    > "$OUT_LOG"
    > "$ERR_LOG"
    
    # 后台启动服务
    (
        cd "$PROJECT_DIR"
        export PYTHONPATH="$PROJECT_DIR"
        export HOST="$HOST"
        export PORT="$PORT"
        export DEFAULT_MODEL="$DEFAULT_MODEL"
        export DEBUG="$DEBUG"
        
        exec ./venv/bin/python3 -m kimi_code_proxy >> "$OUT_LOG" 2>> "$ERR_LOG"
    ) &
    
    local pid=$!
    echo $pid > "$PID_FILE"
    
    # 等待服务启动
    sleep 3
    
    if is_running; then
        echo "✅ 服务已启动 (PID: $pid)"
        echo "   API 地址: http://$HOST:$PORT"
        echo "   日志文件: $OUT_LOG, $ERR_LOG"
    else
        echo "❌ 服务启动失败，请检查日志: $ERR_LOG"
        rm -f "$PID_FILE"
        return 1
    fi
}

cmd_stop() {
    local pid=""
    
    # 优先从 PID 文件获取
    if is_running; then
        pid=$(get_pid)
    fi
    
    # 如果 PID 文件失效，尝试通过端口查找
    if [[ -z "$pid" ]]; then
        pid=$(get_pid_by_port)
        if [[ -n "$pid" ]]; then
            echo "通过端口 $PORT 找到服务进程 (PID: $pid)"
        fi
    fi
    
    if [[ -z "$pid" ]]; then
        echo "服务未运行"
        rm -f "$PID_FILE"
        return 0
    fi
    
    echo "正在停止服务 (PID: $pid)..."
    
    # 先尝试优雅终止
    kill "$pid" 2>/dev/null || true
    
    # 等待最多 5 秒
    local count=0
    while kill -0 "$pid" 2>/dev/null && [[ $count -lt 5 ]]; do
        sleep 1
        ((count++))
    done
    
    # 强制终止
    if kill -0 "$pid" 2>/dev/null; then
        echo "强制终止服务..."
        kill -9 "$pid" 2>/dev/null || true
        sleep 1
    fi
    
    rm -f "$PID_FILE"
    echo "✅ 服务已停止"
}

cmd_run() {
    # 前台运行（调试用）
    ensure_deps
    ensure_dirs
    
    echo "前台运行 Kimi2Moon 服务..."
    echo "按 Ctrl+C 停止"
    
    cd "$PROJECT_DIR"
    export PYTHONPATH="$PROJECT_DIR"
    export HOST="$HOST"
    export PORT="$PORT"
    export DEFAULT_MODEL="$DEFAULT_MODEL"
    export DEBUG="$DEBUG"
    
    ./venv/bin/python3 -m kimi_code_proxy
}

cmd_status() {
    local pid=""
    
    if is_running; then
        pid=$(get_pid)
    fi
    
    if [[ -z "$pid" ]]; then
        pid=$(get_pid_by_port)
    fi
    
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
        echo "✅ 服务运行中 (PID: $pid)"
        echo "   API 地址: http://$HOST:$PORT"
        
        # 显示进程信息
        ps -p "$pid" -o pid,ppid,%cpu,%mem,etime,command 2>/dev/null || true
        
        # 显示端口监听
        echo ""
        echo "端口监听状态:"
        lsof -Pi :"$PORT" -sTCP:LISTEN 2>/dev/null || echo "  无法获取端口信息"
    else
        echo "❌ 服务未运行"
        rm -f "$PID_FILE"
        return 1
    fi
}

cmd_logs() {
    ensure_dirs
    touch "$OUT_LOG" "$ERR_LOG"
    echo "正在监控日志 (按 Ctrl+C 退出)..."
    echo "输出日志: $OUT_LOG"
    echo "错误日志: $ERR_LOG"
    echo ""
    tail -f "$OUT_LOG" "$ERR_LOG"
}

cmd_restart() {
    cmd_stop
    sleep 1
    cmd_start
}

# 主命令处理
cmd="${1:-}"
case "$cmd" in
    start)
        cmd_start
        ;;
    stop)
        cmd_stop
        ;;
    restart)
        cmd_restart
        ;;
    status)
        cmd_status
        ;;
    logs)
        cmd_logs
        ;;
    run)
        cmd_run
        ;;
    *)
        print_help
        exit 1
        ;;
esac

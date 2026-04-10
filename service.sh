#!/bin/bash
# Kimi2Moon launchd 服务管理脚本 (macOS)

set -euo pipefail

LABEL="com.kimi2moon.service"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLIST_DIR="$HOME/Library/LaunchAgents"
PLIST_FILE="$PLIST_DIR/$LABEL.plist"
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
  install     生成 LaunchAgent 配置文件
  enable      安装并启用服务（开机自启 + 立即启动）
  disable     停止并禁用服务（保留配置）
  start       启动服务
  stop        停止服务
  restart     重启服务
  status      查看服务状态
  logs        查看服务日志（持续输出）
  uninstall   卸载服务并删除配置

可选环境变量:
  HOST, PORT, DEFAULT_MODEL, DEBUG
EOF
}

ensure_dirs() {
    mkdir -p "$PLIST_DIR"
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

create_plist() {
    ensure_dirs
    local python_bin
    python_bin="$(resolve_python)"

    cat > "$PLIST_FILE" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$LABEL</string>

    <key>ProgramArguments</key>
    <array>
        <string>$python_bin</string>
        <string>-m</string>
        <string>kimi_code_proxy</string>
    </array>

    <key>WorkingDirectory</key>
    <string>$PROJECT_DIR</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>HOST</key>
        <string>$HOST</string>
        <key>PORT</key>
        <string>$PORT</string>
        <key>DEFAULT_MODEL</key>
        <string>$DEFAULT_MODEL</string>
        <key>DEBUG</key>
        <string>$DEBUG</string>
    </dict>

    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>$OUT_LOG</string>
    <key>StandardErrorPath</key>
    <string>$ERR_LOG</string>
</dict>
</plist>
EOF
    echo "已生成配置: $PLIST_FILE"
}

load_service() {
    launchctl bootout "gui/$(id -u)/$LABEL" >/dev/null 2>&1 || true
    launchctl bootstrap "gui/$(id -u)" "$PLIST_FILE"
    launchctl enable "gui/$(id -u)/$LABEL"
    launchctl kickstart -k "gui/$(id -u)/$LABEL"
}

unload_service() {
    launchctl bootout "gui/$(id -u)/$LABEL" >/dev/null 2>&1 || true
    launchctl disable "gui/$(id -u)/$LABEL" >/dev/null 2>&1 || true
}

cmd="${1:-}"
case "$cmd" in
    install)
        ensure_deps
        create_plist
        ;;
    enable)
        ensure_deps
        create_plist
        load_service
        echo "服务已启用并启动: $LABEL"
        ;;
    disable)
        unload_service
        echo "服务已禁用并停止: $LABEL"
        ;;
    start)
        if [[ ! -f "$PLIST_FILE" ]]; then
            echo "未找到配置文件，先执行: ./service.sh install"
            exit 1
        fi
        load_service
        echo "服务已启动: $LABEL"
        ;;
    stop)
        unload_service
        echo "服务已停止: $LABEL"
        ;;
    restart)
        if [[ ! -f "$PLIST_FILE" ]]; then
            echo "未找到配置文件，先执行: ./service.sh install"
            exit 1
        fi
        unload_service
        load_service
        echo "服务已重启: $LABEL"
        ;;
    status)
        if launchctl print "gui/$(id -u)/$LABEL" >/dev/null 2>&1; then
            echo "服务运行中: $LABEL"
            launchctl print "gui/$(id -u)/$LABEL" | rg "state =|pid =|last exit code =|path ="
        else
            echo "服务未运行: $LABEL"
            exit 1
        fi
        ;;
    logs)
        ensure_dirs
        touch "$OUT_LOG" "$ERR_LOG"
        echo "输出日志: $OUT_LOG"
        echo "错误日志: $ERR_LOG"
        tail -f "$OUT_LOG" "$ERR_LOG"
        ;;
    uninstall)
        unload_service
        rm -f "$PLIST_FILE"
        echo "服务配置已删除: $PLIST_FILE"
        ;;
    *)
        print_help
        exit 1
        ;;
esac

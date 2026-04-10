#!/bin/bash
# Kimi2Moon 一键初始化脚本 (macOS)

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${PROJECT_DIR}/venv"
PYTHON_BIN=""

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_ok() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_err() {
    echo -e "${RED}[ERR]${NC} $1"
}

check_python() {
    if ! command -v python3 >/dev/null 2>&1; then
        log_err "未找到 python3，请先安装 Python 3。"
        exit 1
    fi
    log_ok "检测到 Python: $(python3 --version)"
}

setup_venv() {
    if [[ ! -d "$VENV_DIR" ]]; then
        log_info "创建虚拟环境: $VENV_DIR"
        python3 -m venv "$VENV_DIR"
    else
        log_info "复用现有虚拟环境: $VENV_DIR"
    fi

    PYTHON_BIN="$VENV_DIR/bin/python3"
    if [[ ! -x "$PYTHON_BIN" ]]; then
        log_err "虚拟环境中的 python3 不可用。"
        exit 1
    fi
}

install_deps() {
    log_info "安装/更新 pip 与项目依赖"
    "$PYTHON_BIN" -m pip install --upgrade pip >/dev/null
    "$PYTHON_BIN" -m pip install -r "$PROJECT_DIR/requirements.txt"
    log_ok "依赖安装完成"
}

check_kimi_cli() {
    if command -v kimi >/dev/null 2>&1; then
        log_ok "检测到 Kimi CLI: $(kimi --version 2>/dev/null || echo '已安装')"
    else
        log_warn "未检测到 kimi 命令，请先安装 Kimi Code CLI。"
    fi

    local creds_file="$HOME/.kimi/credentials/kimi-code.json"
    if [[ -f "$creds_file" ]]; then
        log_ok "检测到 Kimi 凭证: $creds_file"
    else
        log_warn "未检测到 Kimi 凭证，请执行: kimi --login"
    fi
}

enable_service() {
    log_info "启用 launchd 服务"
    (cd "$PROJECT_DIR" && ./service.sh enable)
    log_ok "服务已启用"
}

print_done() {
    cat <<EOF

========================================
初始化完成。常用命令：
  ./service.sh status
  ./service.sh logs
  ./service.sh restart
========================================
EOF
}

main() {
    log_info "开始一键初始化 Kimi2Moon"
    check_python
    setup_venv
    install_deps
    check_kimi_cli
    enable_service
    print_done
}

main "$@"

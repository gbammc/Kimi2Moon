#!/bin/bash
# Kimi2Moon 启动脚本

set -e

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🌙 启动 Kimi2Moon...${NC}"

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ 错误: 未找到 Python3${NC}"
    exit 1
fi

# 检查虚拟环境
if [ -d "venv" ]; then
    echo -e "${BLUE}📦 激活虚拟环境...${NC}"
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo -e "${BLUE}📦 激活虚拟环境...${NC}"
    source .venv/bin/activate
fi

# 检查依赖
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  未安装依赖，正在安装...${NC}"
    pip install -r requirements.txt
fi

# 检查 Kimi CLI
if ! command -v kimi &> /dev/null; then
    echo -e "${YELLOW}⚠️  警告: 未找到 Kimi CLI${NC}"
    echo "   请确保已安装 Kimi Code CLI"
else
    echo -e "${GREEN}✅ 已检测到 Kimi CLI${NC}"
fi

# 检查凭证文件
CREDS_FILE="$HOME/.kimi/credentials/kimi-code.json"
if [ ! -f "$CREDS_FILE" ]; then
    echo -e "${YELLOW}⚠️  警告: 未找到 Kimi Code 凭证文件${NC}"
    echo "   路径: $CREDS_FILE"
    echo "   请运行: kimi --login"
else
    echo -e "${GREEN}✅ 已找到凭证文件${NC}"
fi

# 启动服务器
echo -e "${GREEN}🚀 启动服务器...${NC}"
python3 -m kimi_code_proxy "$@"

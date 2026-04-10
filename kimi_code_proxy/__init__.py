"""
Kimi2Moon

将 Kimi Code 包装成 OpenAI 兼容格式的代理服务器
通过调用 kimi CLI 命令使用 Kimi Code

使用方法:
    python -m kimi_code_proxy
"""

__version__ = "2.0.0"
__author__ = "Kimi2Moon"

from .main import app, main

__all__ = ["app", "main"]

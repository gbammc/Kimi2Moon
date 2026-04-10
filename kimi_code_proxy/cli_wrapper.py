"""
Kimi Code CLI 包装器

通过调用 kimi CLI 命令来使用 Kimi Code，绕过 API 直接调用的限制
"""

import json
import subprocess
import asyncio
import os
from typing import List, Dict, Any, Optional, AsyncGenerator
from pathlib import Path

from .cli_parser import extract_reply_text, parse_streaming_output


class KimiCodeCLIWrapper:
    """包装 kimi CLI 命令"""
    
    def __init__(self):
        self.kimi_path = self._find_kimi_cli()
    
    def _find_kimi_cli(self) -> Optional[str]:
        """查找 kimi CLI 路径"""
        # 常见安装位置
        possible_paths = [
            "kimi",  # PATH 中
            "/usr/local/bin/kimi",
            "/usr/bin/kimi",
            os.path.expanduser("~/.local/bin/kimi"),
            os.path.expanduser("~/.cargo/bin/kimi"),  # cargo 安装
        ]
        
        for path in possible_paths:
            try:
                result = subprocess.run(
                    [path, "--version"],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    return path
            except (subprocess.SubprocessError, FileNotFoundError):
                continue
        
        return None
    
    def is_available(self) -> bool:
        """检查 kimi CLI 是否可用"""
        return self.kimi_path is not None
    
    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        model: str = "kimi/k2.5",
        stream: bool = False,
        temperature: float = 0.7,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        使用 kimi CLI 进行聊天补全
        
        使用 --print 模式获取非交互式输出
        """
        if not self.kimi_path:
            raise RuntimeError("Kimi CLI 未找到。请安装: https://kimi.com")
        
        # 构建提示词（从 messages 中提取）
        prompt = self._extract_prompt(messages)
        
        # 构建命令
        # 使用 --print 模式从 stdin 读取输入
        cmd = [
            self.kimi_path,
            "--print",           # 非交互式输出
        ]
        
        # 使用 asyncio 创建子进程
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        
        # 发送提示词到 stdin
        stdout, stderr = await process.communicate(input=prompt.encode('utf-8'))
        
        if process.returncode != 0:
            error_msg = stderr.decode('utf-8', errors='replace') if stderr else "未知错误"
            raise RuntimeError(f"Kimi CLI 错误 (code {process.returncode}): {error_msg}")
        
        output = stdout.decode('utf-8', errors='replace')
        
        if stream:
            # 流式输出 - 逐行解析并发送
            lines = output.split('\n')
            for line in lines:
                parsed = parse_streaming_output(line)
                if parsed and parsed["type"] == "content":
                    yield parsed["content"]
        else:
            # 非流式 - 提取完整回复
            reply = extract_reply_text(output)
            yield reply
    
    def _extract_prompt(self, messages: List[Dict[str, Any]]) -> str:
        """从 messages 中提取提示词"""
        parts = []
        
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            
            if role == "system":
                parts.append(f"[System Instructions]\n{content}")
            elif role == "user":
                parts.append(content)
            elif role == "assistant":
                parts.append(f"[Previous Assistant Response]\n{content}")
        
        # 合并所有内容
        if parts:
            return "\n\n".join(parts)
        
        return "Hello"
    
    def check_auth(self) -> Dict[str, Any]:
        """检查认证状态"""
        if not self.kimi_path:
            return {
                "available": False,
                "error": "Kimi CLI 未安装"
            }
        
        # 检查凭证文件是否存在
        creds_path = Path.home() / ".kimi" / "credentials" / "kimi-code.json"
        if not creds_path.exists():
            return {
                "available": True,
                "authenticated": False,
                "error": "未找到凭证文件，请运行: kimi login"
            }
        
        try:
            # 读取凭证文件
            with open(creds_path, 'r') as f:
                creds = json.load(f)
            
            # 检查 token 是否过期
            import time
            expires_at = creds.get("expires_at")
            if expires_at and time.time() > expires_at:
                return {
                    "available": True,
                    "authenticated": False,
                    "error": "Token 已过期，请重新登录: kimi login"
                }
            
            # 尝试运行 kimi info 验证
            result = subprocess.run(
                [self.kimi_path, "info"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return {
                    "available": True,
                    "authenticated": True,
                    "version": self.get_version()
                }
            else:
                return {
                    "available": True,
                    "authenticated": False,
                    "error": "Kimi CLI 无法正常运行"
                }
                
        except subprocess.TimeoutExpired:
            return {
                "available": True,
                "authenticated": False,
                "error": "检查超时"
            }
        except Exception as e:
            return {
                "available": True,
                "authenticated": False,
                "error": str(e)
            }
    
    def get_version(self) -> Optional[str]:
        """获取 kimi CLI 版本"""
        if not self.kimi_path:
            return None
        
        try:
            result = subprocess.run(
                [self.kimi_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        
        return None


# 全局实例
kimi_cli = KimiCodeCLIWrapper()

"""
解析 Kimi CLI 的输出格式

Kimi CLI --print 模式输出类似 Python 对象的格式，需要解析提取文本内容
"""

import re
from typing import List, Dict, Any, Optional


def parse_kimi_output(output: str) -> Dict[str, Any]:
    """
    解析 Kimi CLI 的输出
    """
    result = {
        "text_parts": [],
        "think_parts": [],
        "status": None,
        "session_id": None
    }
    
    # 使用正则表达式查找所有 TextPart
    # TextPart 可能跨越多行
    text_pattern = r"TextPart\(\s*type='text',\s*text='((?:[^']|\\')*?)'\s*\)"
    for match in re.finditer(text_pattern, output, re.DOTALL):
        text = match.group(1)
        # 处理转义
        text = text.replace("\\'", "'")
        text = text.replace('\\n', '\n')
        text = text.replace('\\t', '\t')
        text = text.replace('\\\\', '\\')
        if text:
            result["text_parts"].append(text)
    
    # 查找 ThinkPart
    think_pattern = r"ThinkPart\(\s*type='think',\s*think='((?:[^']|\\')*?)'"
    for match in re.finditer(think_pattern, output, re.DOTALL):
        think = match.group(1)
        think = think.replace("\\'", "'")
        think = think.replace('\\n', '\n')
        if think:
            result["think_parts"].append(think)
    
    # 查找会话 ID
    session_match = re.search(r'To resume this session: kimi -r ([a-f0-9-]+)', output)
    if session_match:
        result["session_id"] = session_match.group(1)
    
    return result


def extract_reply_text(output: str) -> str:
    """
    从 Kimi CLI 输出中提取回复文本
    
    这是主要的导出函数，返回纯文本回复
    """
    parsed = parse_kimi_output(output)
    
    # 合并所有 TextPart
    text_parts = parsed.get("text_parts", [])
    if text_parts:
        return "\n".join(text_parts)
    
    # 如果没有找到 TextPart，尝试直接提取
    # 有时输出格式可能略有不同
    return output.strip()


def parse_streaming_output(line: str) -> Optional[Dict[str, Any]]:
    """
    解析单行输出（用于流式模拟）
    
    返回:
    - None: 忽略的行
    - dict: 包含 type 和 content 的字典
    """
    line = line.strip()
    
    if not line:
        return None
    
    # 解析文本内容 - 单行版本
    if line.startswith("TextPart(") and "type='text'" in line:
        match = re.search(r"text='((?:[^'\\]|\\.)*)'", line)
        if match:
            text = match.group(1)
            text = text.replace("\\'", "'")
            text = text.replace('\\n', '\n')
            return {"type": "content", "content": text}
    
    # 解析结束
    if line == "TurnEnd()":
        return {"type": "end", "content": None}
    
    if line.startswith("TurnBegin("):
        return {"type": "begin", "content": None}
    
    # 忽略其他元数据行
    return None

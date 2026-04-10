"""
Kimi2Moon API Proxy Server (CLI 版本)

通过调用 kimi CLI 命令来使用 Kimi Code，绕过 API 直接调用的限制

使用方法:
1. 确保已安装并登录 Kimi Code CLI
2. 运行服务器: python -m kimi_code_proxy.main_v2
3. 使用 OpenAI 客户端连接: base_url="http://localhost:8000/v1"
"""

import os
import json
import time
import asyncio
from typing import Optional, AsyncGenerator, List, Dict, Any, Union
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import uvicorn

from .cli_wrapper import kimi_cli


# ============== 配置 ==============
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "kimi/k2.5")

# 可用模型列表
AVAILABLE_MODELS = [
    {"id": "kimi/k2.5", "name": "Kimi K2.5 Coding", "context_window": 256000},
    {"id": "kimi/k2", "name": "Kimi K2 Coding", "context_window": 256000},
]


# ============== 数据模型 ==============

class Message(BaseModel):
    role: str = Field(..., description="消息角色: system, user, assistant")
    content: str = Field(..., description="消息内容")


class ChatCompletionRequest(BaseModel):
    model: str = Field(default=DEFAULT_MODEL, description="模型ID")
    messages: List[Message] = Field(..., description="消息列表")
    temperature: Optional[float] = Field(0.7, ge=0, le=2)
    top_p: Optional[float] = Field(1.0, ge=0, le=1)
    max_tokens: Optional[int] = Field(None, ge=1)
    stream: Optional[bool] = Field(False)
    stop: Optional[Union[str, List[str]]] = Field(None)
    presence_penalty: Optional[float] = Field(0, ge=-2, le=2)
    frequency_penalty: Optional[float] = Field(0, ge=-2, le=2)


class ChatCompletionChoice(BaseModel):
    index: int
    message: Optional[Dict[str, Any]] = None
    delta: Optional[Dict[str, Any]] = None
    finish_reason: Optional[str] = None


class Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(BaseModel):
    id: str
    object: str
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: Usage


class ModelInfo(BaseModel):
    id: str
    object: str = "model"
    created: int
    owned_by: str = "kimi"


class ModelsResponse(BaseModel):
    object: str = "list"
    data: List[ModelInfo]


# ============== 辅助函数 ==============

def generate_id(prefix: str = "chatcmpl") -> str:
    """生成唯一ID"""
    import uuid
    return f"{prefix}-{uuid.uuid4().hex[:24]}"


def now_timestamp() -> int:
    """获取当前时间戳"""
    return int(time.time())


def estimate_tokens(text: str) -> int:
    """估算 token 数量（粗略估计）"""
    # 中文约占 1.5-2 tokens/字符，英文约占 0.25 tokens/字符
    # 这里使用简化估算
    return len(text) // 2 + 1


# ============== FastAPI 应用 ==============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    print("🔍 检查 Kimi Code CLI...")
    
    if not kimi_cli.is_available():
        print("❌ 未找到 Kimi CLI")
        print("   请安装 Kimi Code CLI: https://kimi.com")
    else:
        version = kimi_cli.get_version()
        print(f"✅ 找到 Kimi CLI: {version}")
        
        auth_status = kimi_cli.check_auth()
        if auth_status.get("authenticated"):
            print(f"✅ 已登录: {auth_status.get('user', 'Unknown')}")
        else:
            print(f"⚠️  未登录: {auth_status.get('error', '请运行 kimi --login')}")
    
    yield
    print("\n👋 服务器关闭")


app = FastAPI(
    title="Kimi2Moon (CLI)",
    description="通过 CLI 调用 Kimi Code 的 OpenAI 兼容代理",
    version="2.0.0",
    lifespan=lifespan
)


# ============== API 端点 ==============

@app.get("/")
async def root():
    """根路径 - 服务信息"""
    return {
        "name": "Kimi2Moon (CLI)",
        "version": "2.0.0",
        "description": "通过 CLI 调用 Kimi Code 的 OpenAI 兼容代理",
        "note": "此代理通过调用 kimi CLI 命令使用 Kimi Code",
        "endpoints": {
            "models": "/v1/models",
            "chat_completions": "/v1/chat/completions"
        },
        "documentation": "/docs",
        "kimi_cli_available": kimi_cli.is_available(),
        "kimi_cli_version": kimi_cli.get_version(),
    }


@app.get("/v1")
async def v1_root():
    """
    OpenAI API v1 根路径
    
    一些客户端（如 Cursor）会访问此路径来验证 API 可用性
    """
    return {
        "object": "list",
        "data": [
            {
                "id": "kimi/k2.5",
                "object": "model",
                "created": now_timestamp(),
                "owned_by": "kimi"
            }
        ]
    }


@app.get("/v1/models", response_model=ModelsResponse)
async def list_models():
    """获取可用模型列表"""
    models = []
    for m in AVAILABLE_MODELS:
        models.append(ModelInfo(
            id=m["id"],
            created=int(time.time())
        ))
    
    return ModelsResponse(data=models)


@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(request: ChatCompletionRequest):
    """
    聊天补全接口
    
    通过调用 kimi CLI 实现
    """
    if not kimi_cli.is_available():
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Kimi CLI 不可用",
                "message": "未找到 Kimi CLI。请安装: https://kimi.com",
                "type": "service_unavailable"
            }
        )
    
    auth_status = kimi_cli.check_auth()
    if not auth_status.get("authenticated"):
        raise HTTPException(
            status_code=401,
            detail={
                "error": "未认证",
                "message": f"Kimi CLI 未登录。请运行: kimi --login",
                "type": "authentication_error"
            }
        )
    
    try:
        if request.stream:
            # 流式响应
            return StreamingResponse(
                stream_chat_completion(request),
                media_type="text/event-stream"
            )
        else:
            # 非流式响应
            return await non_stream_chat_completion(request)
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Kimi CLI 错误",
                "message": str(e),
                "type": "internal_error"
            }
        )


async def non_stream_chat_completion(request: ChatCompletionRequest) -> ChatCompletionResponse:
    """非流式聊天补全"""
    # 调用 kimi CLI
    output = ""
    async for chunk in kimi_cli.chat_completion(
        messages=[m.model_dump() for m in request.messages],
        model=request.model,
        stream=False,
        temperature=request.temperature
    ):
        output += chunk
    
    # 估算 token
    prompt_text = "\n".join(m.content for m in request.messages)
    prompt_tokens = estimate_tokens(prompt_text)
    completion_tokens = estimate_tokens(output)
    
    return ChatCompletionResponse(
        id=generate_id(),
        object="chat.completion",
        created=now_timestamp(),
        model=request.model,
        choices=[
            ChatCompletionChoice(
                index=0,
                message={
                    "role": "assistant",
                    "content": output.strip()
                },
                finish_reason="stop"
            )
        ],
        usage=Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens
        )
    )


async def stream_chat_completion(request: ChatCompletionRequest) -> AsyncGenerator[str, None]:
    """流式聊天补全（模拟）"""
    chunk_id = generate_id()
    created = now_timestamp()
    
    # 发送开始消息
    start_chunk = {
        "id": chunk_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": request.model,
        "choices": [{
            "index": 0,
            "delta": {"role": "assistant"},
            "finish_reason": None
        }]
    }
    yield f"data: {json.dumps(start_chunk, ensure_ascii=False)}\n\n"
    
    # 调用 kimi CLI 获取完整输出，然后分块发送
    # 注意：kimi CLI 本身不支持真正的流式，这里模拟流式效果
    output = ""
    async for chunk in kimi_cli.chat_completion(
        messages=[m.model_dump() for m in request.messages],
        model=request.model,
        stream=False
    ):
        output += chunk
    
    # 模拟流式输出（每 10 个字符发送一次）
    content = output.strip()
    chunk_size = 10
    
    for i in range(0, len(content), chunk_size):
        text_chunk = content[i:i+chunk_size]
        
        delta_chunk = {
            "id": chunk_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": request.model,
            "choices": [{
                "index": 0,
                "delta": {"content": text_chunk},
                "finish_reason": None
            }]
        }
        yield f"data: {json.dumps(delta_chunk, ensure_ascii=False)}\n\n"
        
        # 小延迟模拟流式效果
        await asyncio.sleep(0.01)
    
    # 发送结束消息
    end_chunk = {
        "id": chunk_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": request.model,
        "choices": [{
            "index": 0,
            "delta": {},
            "finish_reason": "stop"
        }]
    }
    yield f"data: {json.dumps(end_chunk, ensure_ascii=False)}\n\n"
    yield "data: [DONE]\n\n"


@app.get("/health")
async def health_check():
    """健康检查端点"""
    auth_status = kimi_cli.check_auth()
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "kimi_cli_available": kimi_cli.is_available(),
        "kimi_cli_version": kimi_cli.get_version(),
        "kimi_authenticated": auth_status.get("authenticated", False),
        "kimi_user": auth_status.get("user")
    }


# ============== 主入口 ==============

def main():
    """运行服务器"""
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║            🌙 Kimi2Moon Server (CLI 版本) 🌙                ║
╠══════════════════════════════════════════════════════════════╣
║  注意: 此代理通过调用 kimi CLI 命令使用 Kimi Code            ║
║  请确保已安装 Kimi Code CLI 并登录                           ║
╠══════════════════════════════════════════════════════════════╣
║  文档: http://{host}:{port}/docs                            ║
║  健康检查: http://{host}:{port}/health                      ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    uvicorn.run(
        "kimi_code_proxy.main:app",
        host=host,
        port=port,
        reload=os.getenv("DEBUG", "false").lower() == "true"
    )


if __name__ == "__main__":
    main()

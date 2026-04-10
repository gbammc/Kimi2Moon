# Kimi2Moon

把本地 `kimi` CLI 包装成 OpenAI 兼容接口，方便 OpenAI SDK / 客户端直接接入。

## 快速开始（推荐）

前提：

```bash
kimi --version
kimi login
```

一键初始化并启用服务（macOS）：

```bash
./setup.sh
```

完成后默认地址：`http://localhost:8000`
- 文档：`/docs`
- 健康检查：`/health`

## 手动启动

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
./start.sh
```

服务默认监听 `http://localhost:8000`。

## 服务管理（macOS）

```bash
./service.sh enable     # 安装 + 开机自启 + 立即启动
./service.sh status
./service.sh restart
./service.sh logs
./service.sh disable
./service.sh uninstall
```

可通过环境变量覆盖配置：

```bash
HOST=0.0.0.0 PORT=8000 DEFAULT_MODEL=kimi/k2.5 DEBUG=false ./service.sh enable
```

## 使用示例

```python
from openai import OpenAI

client = OpenAI(
    api_key="dummy-key",
    base_url="http://localhost:8000/v1",
)

resp = client.chat.completions.create(
    model="kimi/k2.5",
    messages=[{"role": "user", "content": "你好，介绍下你自己"}],
)
print(resp.choices[0].message.content)
```

### cURL

```bash
curl http://localhost:8000/v1/models

curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dummy-key" \
  -d '{
    "model": "kimi/k2.5",
    "messages": [{"role": "user", "content": "你好！"}]
  }'
```

## 配置

| 变量 | 默认值 | 说明 |
|---|---|---|
| `DEFAULT_MODEL` | `kimi/k2.5` | 默认模型 |
| `HOST` | `0.0.0.0` | 监听地址 |
| `PORT` | `8000` | 监听端口 |
| `DEBUG` | `false` | 调试模式 |

## License

MIT

# 🎯 代理配置快速参考

## 📝 配置文件 (.env)

```bash
# 代理地址
HTTP_PROXY=http://127.0.0.1:10808
HTTPS_PROXY=http://127.0.0.1:10808

# 需要代理的服务（逗号分隔）
PROXY_ENABLED_SERVICES=gemini,fishaudio
```

## 💻 代码使用

### 方式1: HTTP 客户端（推荐用于 REST API）

```python
from app.core.http_client import create_http_client

# 自动应用代理
client = create_http_client("fishaudio")
response = client.post(url, json=data)
```

### 方式2: 直接获取代理字典

```python
from app.core.proxy_config import get_proxy_for_service

proxies = get_proxy_for_service("gemini")
# 返回: {"http": "...", "https": "..."} 或 None

import requests
response = requests.get(url, proxies=proxies)
```

### 方式3: Google SDK（自动）

```python
# GeminiService 会自动设置环境变量
gemini = GeminiService()  # 自动应用代理
```

## 🧪 测试

```bash
# 运行测试脚本
python test_proxy.py

# 输出示例：
# gemini: ✅ 使用代理
# fishaudio: ✅ 使用代理  
# liblib: ❌ 不使用代理
```

## 🔧 故障排查

```bash
# 1. 检查代理是否运行
curl -x http://127.0.0.1:10808 https://www.google.com

# 2. 查看配置
python test_proxy.py

# 3. 检查环境变量
echo $env:HTTP_PROXY
```

## ✨ 服务列表

| 服务 | 需要代理 | 配置值 |
|------|---------|-------|
| gemini | ✅ | gemini |
| fishaudio | ✅ | fishaudio |
| liblib | ❌ | - |
| nca | ❌ | - |
| fal | 🔄 | fal (可选) |

## 📚 完整文档

详见: `docs/PROXY_CONFIG.md`

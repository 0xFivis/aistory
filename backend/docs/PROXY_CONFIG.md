# 代理配置说明

## 概述

由于某些外部服务（如 Gemini、Fish Audio）需要通过代理访问，系统提供了灵活的代理配置机制。

## 配置方法

### 1. 编辑 `.env` 文件

```bash
# 代理配置（用于访问国外服务）
HTTP_PROXY=http://127.0.0.1:7890
HTTPS_PROXY=http://127.0.0.1:7890
# 需要代理的服务列表（逗号分隔）
PROXY_ENABLED_SERVICES=gemini,fishaudio
```

**参数说明：**

- `HTTP_PROXY`: HTTP 代理地址（支持 http://、socks5:// 协议）
- `HTTPS_PROXY`: HTTPS 代理地址
- `PROXY_ENABLED_SERVICES`: 需要使用代理的服务列表，逗号分隔
  - 可选值: `gemini`, `fishaudio`, `liblib`, `nca`, `fal`, `cloudinary`
  - 只有在此列表中的服务才会使用代理

### 2. 支持的代理类型

- **HTTP 代理**: `http://host:port`
- **HTTPS 代理**: `https://host:port`
- **SOCKS5 代理**: `socks5://host:port` （需要安装 `pysocks`）

### 3. 常见代理软件端口

- **Clash**: `http://127.0.0.1:7890`
- **V2Ray**: `http://127.0.0.1:10809`
- **Shadowsocks**: `socks5://127.0.0.1:1080`

## 架构说明

### 核心模块

1. **`app/core/proxy_config.py`** - 代理配置管理
   - `ProxyConfig` 类：解析和管理代理配置
   - `get_proxy_for_service(service_name)`: 获取指定服务的代理配置

2. **`app/core/http_client.py`** - HTTP 客户端（自动代理）
   - `ProxyHTTPClient` 类：封装 requests，自动应用代理
   - `create_http_client(service_name)`: 创建 HTTP 客户端

### 使用示例

#### 方式1: 使用 ProxyHTTPClient（推荐）

```python
from app.core.http_client import create_http_client

# 创建支持代理的客户端
client = create_http_client("fishaudio")

# 发送请求（自动使用代理）
response = client.post(
    "https://api.fish.audio/v1/tts",
    json={"text": "你好"},
    headers={"Authorization": f"Bearer {api_key}"}
)
```

#### 方式2: 直接使用 requests

```python
from app.core.proxy_config import get_proxy_for_service

proxies = get_proxy_for_service("gemini")
# proxies = {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"} 或 None

response = requests.get(url, proxies=proxies)
```

#### 方式3: Google SDK（自动读取环境变量）

Gemini Service 在初始化时会自动设置环境变量：

```python
class GeminiService(BaseService):
    def __init__(self):
        self._setup_proxy()  # 自动设置 HTTP_PROXY 环境变量
        self._configure_client()
```

## 服务代理配置表

| 服务名称      | 是否需要代理 | 配置值              | 说明                    |
|--------------|------------|--------------------|-----------------------|
| gemini       | ✅ 是      | `gemini`           | Google Gemini API      |
| fishaudio    | ✅ 是      | `fishaudio`        | Fish Audio TTS         |
| liblib       | ❌ 否      | -                  | Liblib AI (国内服务)    |
| nca          | ❌ 否      | -                  | NCA Toolkit (本地服务)  |
| fal          | 🔄 可选    | `fal`              | Fal AI (根据网络情况)   |
| cloudinary   | 🔄 可选    | `cloudinary`       | Cloudinary (根据网络)   |

## 测试代理配置

运行测试脚本验证代理是否正确配置：

```bash
cd backend
.\.venv\Scripts\python.exe test_proxy.py
```

测试内容：
1. 显示代理配置信息
2. 检查各服务代理状态
3. 测试 HTTP 客户端创建
4. （可选）真实请求测试

## 故障排查

### 问题1: 代理不生效

**检查清单：**
1. 确认 `.env` 文件中 `HTTP_PROXY` 和 `HTTPS_PROXY` 正确配置
2. 确认服务名称在 `PROXY_ENABLED_SERVICES` 列表中
3. 确认代理软件（Clash/V2Ray）正在运行
4. 检查防火墙是否阻止本地代理端口

**调试方法：**
```bash
# 运行代理测试
python test_proxy.py

# 查看日志
# 日志会显示 "Gemini service configured to use proxy: ..."
```

### 问题2: 连接超时

可能原因：
- 代理地址错误
- 代理软件未启动
- 防火墙阻止

解决方法：
```bash
# 测试代理是否可用
curl -x http://127.0.0.1:7890 https://www.google.com
```

### 问题3: 部分服务不需要代理

如果某个服务不需要代理，从 `PROXY_ENABLED_SERVICES` 中移除：

```bash
# 只给 Gemini 使用代理
PROXY_ENABLED_SERVICES=gemini

# 给多个服务使用代理
PROXY_ENABLED_SERVICES=gemini,fishaudio,fal
```

## 安全提示

1. **不要在代码中硬编码代理地址**，使用环境变量
2. **代理配置仅在 `.env` 文件中**，不要提交到 Git
3. **生产环境**建议使用专用的代理服务器
4. 如果使用 SOCKS5 代理，需要安装: `pip install pysocks`

## 更新日志

- 2025-01-XX: 初始版本，支持 Gemini 和 Fish Audio 代理配置
- 支持服务级别的代理控制
- 提供统一的 HTTP 客户端封装

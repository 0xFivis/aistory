"""HTTP 请求辅助模块 - 支持代理配置"""
import requests
from typing import Optional, Dict, Any
from app.core.proxy_config import get_proxy_for_service


class ProxyHTTPClient:
    """支持代理的 HTTP 客户端"""
    
    def __init__(self, service_name: str, timeout: int = 60):
        """
        Args:
            service_name: 服务名称（用于获取代理配置）
            timeout: 请求超时时间（秒）
        """
        self.service_name = service_name
        self.timeout = timeout
        self.proxies = get_proxy_for_service(service_name)
        self.session = requests.Session()
        # 禁用 requests 默认从环境变量继承代理，完全交由配置中心控制
        self.session.trust_env = False

        # 如果有代理，配置到 session
        if self.proxies:
            self.session.proxies.update(self.proxies)
        else:
            # 显式清空代理字典，确保不会落回系统级设置
            self.session.proxies.clear()
    
    def get(self, url: str, **kwargs) -> requests.Response:
        """GET 请求"""
        kwargs.setdefault("timeout", self.timeout)
        if self.proxies:
            kwargs["proxies"] = self.proxies
        return self.session.get(url, **kwargs)
    
    def post(self, url: str, **kwargs) -> requests.Response:
        """POST 请求"""
        kwargs.setdefault("timeout", self.timeout)
        if self.proxies:
            kwargs["proxies"] = self.proxies
        return self.session.post(url, **kwargs)
    
    def put(self, url: str, **kwargs) -> requests.Response:
        """PUT 请求"""
        kwargs.setdefault("timeout", self.timeout)
        if self.proxies:
            kwargs["proxies"] = self.proxies
        return self.session.put(url, **kwargs)
    
    def delete(self, url: str, **kwargs) -> requests.Response:
        """DELETE 请求"""
        kwargs.setdefault("timeout", self.timeout)
        if self.proxies:
            kwargs["proxies"] = self.proxies
        return self.session.delete(url, **kwargs)
    
    def close(self):
        """关闭会话"""
        self.session.close()


def create_http_client(service_name: str, timeout: int = 30) -> ProxyHTTPClient:
    """快捷函数：创建 HTTP 客户端
    
    Args:
        service_name: 服务名称 (gemini, fishaudio, liblib, etc.)
        timeout: 超时时间
    
    Returns:
        ProxyHTTPClient 实例
    
    Example:
        client = create_http_client("fishaudio")
        response = client.post("https://api.fish.audio/v1/tts", json={...})
    """
    return ProxyHTTPClient(service_name, timeout)

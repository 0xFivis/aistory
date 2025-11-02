"""测试代理配置"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from app.core.proxy_config import proxy_config
from app.core.http_client import create_http_client


def test_proxy_config():
    """测试代理配置是否正确加载"""
    print("\n" + "=" * 60)
    print("【测试1】代理配置信息")
    print("=" * 60)
    
    info = proxy_config.get_proxy_info()
    print(f"HTTP Proxy: {info['http_proxy']}")
    print(f"HTTPS Proxy: {info['https_proxy']}")
    print(f"已配置: {info['is_configured']}")
    print(f"需要代理的服务: {', '.join(info['enabled_services'])}")
    
    print("\n" + "=" * 60)
    print("【测试2】各服务代理状态")
    print("=" * 60)
    
    services = ["gemini", "fishaudio", "liblib", "nca", "fal", "cloudinary"]
    for service in services:
        use_proxy = proxy_config.should_use_proxy(service)
        proxies = proxy_config.get_proxies(service)
        status = "✅ 使用代理" if use_proxy else "❌ 不使用代理"
        print(f"{service:15s}: {status}")
        if proxies:
            print(f"                 {proxies}")


def test_http_client():
    """测试 HTTP 客户端代理配置"""
    print("\n" + "=" * 60)
    print("【测试3】HTTP 客户端测试")
    print("=" * 60)
    
    # 测试需要代理的服务
    print("\n测试 Gemini 客户端（需要代理）:")
    gemini_client = create_http_client("gemini")
    print(f"  代理配置: {gemini_client.proxies}")
    
    print("\n测试 Fish Audio 客户端（需要代理）:")
    fish_client = create_http_client("fishaudio")
    print(f"  代理配置: {fish_client.proxies}")
    
    # 测试不需要代理的服务
    print("\n测试 Liblib 客户端（不需要代理）:")
    liblib_client = create_http_client("liblib")
    print(f"  代理配置: {liblib_client.proxies}")
    
    # 清理
    gemini_client.close()
    fish_client.close()
    liblib_client.close()


def test_real_request():
    """测试真实的 HTTP 请求（可选）"""
    print("\n" + "=" * 60)
    print("【测试4】真实请求测试（可选）")
    print("=" * 60)
    
    # 测试访问 Google（需要代理）
    print("\n尝试访问 Google API（测试代理是否生效）:")
    client = create_http_client("gemini", timeout=10)
    try:
        # 测试一个简单的 Google API 端点
        response = client.get("https://generativelanguage.googleapis.com/v1/models")
        print(f"  状态码: {response.status_code}")
        if response.status_code == 200:
            print("  ✅ 代理工作正常！可以访问 Google API")
        else:
            print(f"  ⚠️  返回状态码 {response.status_code}，可能需要 API Key")
    except Exception as e:
        print(f"  ❌ 请求失败: {e}")
        print("  提示: 请检查代理是否正确配置并运行")
    finally:
        client.close()


def main():
    print("\n🔧 代理配置测试工具")
    print("=" * 60)
    
    # 显示环境变量
    print("\n环境变量:")
    print(f"  HTTP_PROXY: {os.getenv('HTTP_PROXY', '未设置')}")
    print(f"  HTTPS_PROXY: {os.getenv('HTTPS_PROXY', '未设置')}")
    print(f"  PROXY_ENABLED_SERVICES: {os.getenv('PROXY_ENABLED_SERVICES', '未设置')}")
    
    test_proxy_config()
    test_http_client()
    
    # 询问是否进行真实请求测试
    print("\n" + "=" * 60)
    choice = input("是否进行真实请求测试？(y/n): ").strip().lower()
    if choice == 'y':
        test_real_request()
    
    print("\n" + "=" * 60)
    print("✓ 测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()

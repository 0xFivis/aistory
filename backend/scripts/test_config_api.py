"""测试配置管理 API"""
import requests
import json

BASE_URL = "http://localhost:8000/api/v1/config"

def test_add_credentials():
    """测试添加服务凭证"""
    print("\n========== 测试添加凭证 ==========")
    
    # 跳过 Fish Audio（网络问题）
    # print("跳过 Fish Audio...")
    
    # 添加 Liblib 凭证
    data = {
        "service_name": "liblib",
        "credential_type": "access_secret",
        "credential_key": "BuEH8bCVGTHZoFuxaimu5A",
        "credential_secret": "rxyXJeRL0JaK6yvuRR9PSjlQplgqhiD0",
        "api_url": "https://openapi.liblibai.cloud",
        "description": "Liblib AI 图像生成"
    }
    response = requests.post(f"{BASE_URL}/credentials", json=data)
    print(f"\n添加 Liblib: {response.status_code}")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    
    # 添加 NCA 凭证
    data = {
        "service_name": "nca",
        "credential_type": "api_key",
        "credential_key": "g4360509b1c04f008814b52619ec0706",
        "api_url": "https://no-code-architects-toolkit-1092446948801.us-central1.run.app",
        "description": "NCA Toolkit 视频处理"
    }
    response = requests.post(f"{BASE_URL}/credentials", json=data)
    print(f"\n添加 NCA: {response.status_code}")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))


def test_add_options():
    """测试添加可选参数"""
    print("\n\n========== 测试添加可选参数 ==========")
    
    # 跳过 Fish Audio 音色
    print("跳过 Fish Audio 音色...")
    
    # 添加 Liblib LoRA
    loras = [
        {
            "service_name": "liblib",
            "option_type": "lora_id",
            "option_key": "realistic_lora_x",
            "option_value": "a11be034522a43deaf1c9a0e7fb81f61",
            "option_name": "LoRA X-写实风格",
            "description": "3D写实历史人物风格",
            "is_default": True,
            "meta_data": {"trigger_word": "3d render in ti artstyle"}
        },
        {
            "service_name": "liblib",
            "option_type": "lora_id",
            "option_key": "cartoon_lora_y",
            "option_value": "def456ghi789",
            "option_name": "LoRA Y-卡通风格",
            "description": "卡通动漫风格",
            "is_default": False
        }
    ]
    
    for lora in loras:
        response = requests.post(f"{BASE_URL}/options", json=lora)
        print(f"添加 LoRA {lora['option_name']}: {response.status_code}")
    
    # 添加 Liblib 模型
    data = {
        "service_name": "liblib",
        "option_type": "model_id",
        "option_key": "main_model_realistic",
        "option_value": "412b427ddb674b4dbab9e5abd5ae6057",
        "option_name": "主模型-写实风格",
        "description": "写实风格主模型",
        "is_default": True
    }
    response = requests.post(f"{BASE_URL}/options", json=data)
    print(f"添加模型: {response.status_code}")


def test_list_credentials():
    """测试获取凭证列表"""
    print("\n\n========== 测试获取凭证列表 ==========")
    response = requests.get(f"{BASE_URL}/credentials")
    print(f"状态码: {response.status_code}")
    credentials = response.json()
    print(f"凭证数量: {len(credentials)}")
    for cred in credentials:
        print(f"  - {cred['service_name']}: {cred['credential_key']} ({cred['description']})")


def test_list_voices():
    """测试获取音色列表"""
    print("\n\n========== 测试获取音色列表 ==========")
    print("跳过（无 Fish Audio 数据）...")
    return


def test_list_loras():
    """测试获取 LoRA 列表"""
    print("\n\n========== 测试获取 LoRA 列表 ==========")
    response = requests.get(f"{BASE_URL}/options/loras")
    print(f"状态码: {response.status_code}")
    loras = response.json()
    print(f"LoRA 数量: {len(loras)}")
    for lora in loras:
        default = " [默认]" if lora['is_default'] else ""
        print(f"  - {lora['option_name']}{default}: {lora['option_value']}")
        if lora.get('meta_data'):
            print(f"    触发词: {lora['meta_data'].get('trigger_word')}")


if __name__ == "__main__":
    print("=" * 60)
    print("配置管理 API 测试")
    print("=" * 60)
    
    try:
        # 1. 添加凭证
        test_add_credentials()
        
        # 2. 添加可选参数
        test_add_options()
        
        # 3. 查询凭证列表
        test_list_credentials()
        
        # 4. 查询音色列表
        test_list_voices()
        
        # 5. 查询 LoRA 列表
        test_list_loras()
        
        print("\n" + "=" * 60)
        print("✓ 所有测试完成！")
        print("=" * 60)
        
    except requests.exceptions.ConnectionError:
        print("\n❌ 错误：无法连接到服务器")
        print("请先启动服务器: uvicorn app.main:app --reload")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")

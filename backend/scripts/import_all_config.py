"""一键导入所有配置到数据库"""
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

# ==================== 服务凭证 ====================
credentials = [
    {
        "service_name": "gemini",
        "credential_type": "api_key",
        "credential_key": "AIzaSyC-XiYVpz27Vb4CFugFfMNwdAqaBwOnstg",  # 替换为真实的
        "api_url": "https://generativelanguage.googleapis.com",
        "description": "Google Gemini AI"
    },
    {
        "service_name": "fishaudio",
        "credential_type": "api_key",
        "credential_key": "a4360509b1c04f008814b52619e0d535",
        "api_url": "https://api.fish.audio/v1",
        "description": "Fish Audio TTS"
    },
    {
        "service_name": "liblib",
        "credential_type": "access_secret",
        "credential_key": "BuEH8bCVGTHZoFuxaimu5A",
        "credential_secret": "rxyXJeRL0JaK6yvuRR9PSjlQplgqhiD0",
        "api_url": "https://openapi.liblibai.cloud",
        "description": "Liblib AI"
    },
    {
        "service_name": "nca",
        "credential_type": "api_key",
        "credential_key": "g4360509b1c04f008814b52619ec0706",
        "api_url": "http://localhost:8080",
        "description": "NCA Toolkit"
    },
    {
        "service_name": "fal",
        "credential_type": "api_key",
        "credential_key": "902438ad-7716-4065-9290-d8245f79cce9:daa85ae7ab1bf8456c7f2cc16f8b59f9",
        "api_url": "https://api.fal.ai",
        "description": "Fal AI"
    },
    {
        "service_name": "cloudinary",
        "credential_type": "access_secret",
        "credential_key": "637352218498828",  # 替换
        "credential_secret": "f3aTXrfjjMLDhcw4helAhItzoMg",  # 替换
        "description": "Cloudinary 存储"
    }
]

# ==================== 可选参数 ====================
options = [
    # Fish Audio 音色
    {
        "service_name": "fishaudio",
        "option_type": "voice_id",
        "option_key": "male_voice_a",
        "option_value": "d8c7af3779494549a975bdb8015e8a8b",
        "option_name": "音色A-男声",
        "description": "深沉男声",
        "is_default": True
    },
    
    # Liblib 主模型
    {
        "service_name": "liblib",
        "option_type": "model_id",
        "option_key": "main_model",
        "option_value": "412b427ddb674b4dbab9e5abd5ae6057",
        "option_name": "主模型-写实",
        "description": "写实风格主模型",
        "is_default": True
    },
    
    # Liblib LoRA
    {
        "service_name": "liblib",
        "option_type": "lora_id",
        "option_key": "lora_realistic",
        "option_value": "a11be034522a43deaf1c9a0e7fb81f61",
        "option_name": "LoRA-写实",
        "description": "3D写实风格",
        "is_default": True,
        "meta_data": {"trigger_word": "3d render in ti artstyle"}
    },
    
    # Liblib 提示词模板
    {
        "service_name": "liblib",
        "option_type": "prompt_template",
        "option_key": "realistic_template",
        "option_value": "3d render in ti artstyle of a middle-aged man seated alone in a retro-futuristic mid-century modern apartment during golden hour...",
        "option_name": "提示词模板",
        "description": "给Gemini参考的提示词示例",
        "is_default": True
    },
    
    # Gemini 模型
    {
        "service_name": "gemini",
        "option_type": "model_id",
        "option_key": "gemini_pro",
        "option_value": "models/gemini-2.5-pro",
        "option_name": "Gemini 2.5 Pro",
        "description": "主力模型",
        "is_default": True
    }
]

# ==================== 媒体素材 ====================
assets = [
    # 背景音乐
    {
        "asset_type": "bgm",
        "asset_name": "月半小夜曲",
        "file_url": "https://storage.googleapis.com/autoaitt/ai/月半小夜曲.MP3",
        "tags": ["古风", "抒情"],
        "description": "默认背景音乐",
        "is_default": True
    },
    # 可以添加更多背景音乐...
]


def import_all():
    print("=" * 60)
    print("开始导入配置...")
    print("=" * 60)
    
    # 1. 导入凭证
    print("\n【1/3】导入服务凭证...")
    for cred in credentials:
        try:
            response = requests.post(f"{BASE_URL}/config/credentials", json=cred)
            if response.status_code == 200:
                print(f"  ✅ {cred['service_name']}")
            else:
                print(f"  ❌ {cred['service_name']}: {response.status_code}")
        except Exception as e:
            print(f"  ❌ {cred['service_name']}: {e}")
    
    # 2. 导入选项
    print("\n【2/3】导入可选参数...")
    for opt in options:
        try:
            response = requests.post(f"{BASE_URL}/config/options", json=opt)
            if response.status_code == 200:
                print(f"  ✅ {opt['option_name']}")
            else:
                print(f"  ❌ {opt['option_name']}: {response.status_code}")
        except Exception as e:
            print(f"  ❌ {opt['option_name']}: {e}")
    
    # 3. 导入素材
    print("\n【3/3】导入媒体素材...")
    for asset in assets:
        try:
            response = requests.post(f"{BASE_URL}/assets/", json=asset)
            if response.status_code == 200:
                print(f"  ✅ {asset['asset_name']} ({asset['asset_type']})")
            else:
                print(f"  ❌ {asset['asset_name']}: {response.status_code}")
        except Exception as e:
            print(f"  ❌ {asset['asset_name']}: {e}")
    
    print("\n" + "=" * 60)
    print("✓ 配置导入完成！")
    print("=" * 60)
    
    # 4. 验证
    print("\n验证结果：")
    creds = requests.get(f"{BASE_URL}/config/credentials").json()
    opts = requests.get(f"{BASE_URL}/config/options").json()
    bgms = requests.get(f"{BASE_URL}/assets/bgm").json()
    print(f"  凭证数量: {len(creds)}")
    print(f"  选项数量: {len(opts)}")
    print(f"  背景音乐: {len(bgms)}")



if __name__ == "__main__":
    print("\n✅ 所有配置已就绪，开始导入...\n")
    
    import_all()

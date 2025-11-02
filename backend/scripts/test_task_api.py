"""测试重构后的任务管理 API"""
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"


def test_create_task():
    """测试创建任务（使用新的配置系统）"""
    print("\n" + "=" * 60)
    print("【测试1】创建新任务（完整配置）")
    print("=" * 60)
    
    payload = {
        "title": "明朝历史-张居正改革",
        "description": """明朝万历年间，首辅张居正推行了一系列改革措施，
史称"张居正改革"。他整顿吏治，推行"一条鞭法"，
加强中央集权，使明朝国力得到短暂恢复。
然而改革触动了既得利益集团，张居正死后改革被废除。""",
        "reference_video": None,
        "task_config": {
            "scene_count": 6,
            "language": "中文",
            "audio_voice_id": "male_voice_a",
            "liblib_lora_id": "lora_realistic",
            "liblib_model_id": "main_model",
            "bgm_asset_id": 1,
            "provider": "liblib"
        }
    }
    
    try:
        response = requests.post(f"{BASE_URL}/tasks/", json=payload)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 任务创建成功！")
            print(f"  任务ID: {data['id']}")
            print(f"  状态: {data['status']} (0=待处理, 1=处理中, 2=成功, 3=失败)")
            print(f"  进度: {data['progress']}%")
            print(f"  总分镜数: {data['total_scenes']}")
            print(f"  已完成分镜: {data['completed_scenes']}")
            return data['id']
        else:
            print(f"❌ 创建失败: {response.status_code}")
            print(f"  错误: {response.text}")
            return None
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return None


def test_get_task_detail(task_id):
    """测试获取任务详情（包含步骤和分镜）"""
    print("\n" + "=" * 60)
    print(f"【测试2】获取任务详情 (ID={task_id})")
    print("=" * 60)
    
    try:
        response = requests.get(f"{BASE_URL}/tasks/{task_id}")
        if response.status_code == 200:
            data = response.json()
            
            # 任务信息
            task = data['task']
            print(f"\n📋 任务信息:")
            print(f"  ID: {task['id']}")
            print(f"  状态: {task['status']}")
            print(f"  进度: {task['progress']}%")
            print(f"  分镜数: {task['completed_scenes']}/{task['total_scenes']}")
            
            # 步骤信息
            steps = data['steps']
            print(f"\n🔄 任务步骤 ({len(steps)} 个):")
            for step in steps:
                status_text = ["待处理", "处理中", "成功", "失败"][step['status']]
                print(f"  {step['seq']}. {step['step_name']}: {status_text} ({step['progress']}%) - 重试 {step['retry_count']}/{step['max_retries']}")
            
            # 分镜信息
            scenes = data['scenes']
            print(f"\n🎬 分镜列表 ({len(scenes)} 个):")
            for scene in scenes[:3]:  # 只显示前3个
                print(f"  场景 {scene['seq']}: 图片({scene['image_status']}) 音频({scene['audio_status']}) 视频({scene['video_status']})")
                print(f"    旁白: {scene['narration_text'][:30]}...")
                print(f"    提示词: {scene['image_prompt'][:50]}...")
            
            if len(scenes) > 3:
                print(f"  ... 还有 {len(scenes) - 3} 个分镜")
            
            return True
        else:
            print(f"❌ 获取失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return False


def test_list_tasks():
    """测试获取任务列表"""
    print("\n" + "=" * 60)
    print("【测试3】获取任务列表")
    print("=" * 60)
    
    try:
        response = requests.get(f"{BASE_URL}/tasks/", params={"limit": 5})
        if response.status_code == 200:
            tasks = response.json()
            print(f"✅ 共有 {len(tasks)} 个任务:")
            for task in tasks:
                print(f"  - 任务{task['id']}: 状态={task['status']}, 进度={task['progress']}%, 分镜={task['completed_scenes']}/{task['total_scenes']}")
            return True
        else:
            print(f"❌ 获取失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return False


def test_retry_scene(task_id, scene_id):
    """测试重试单个分镜"""
    print("\n" + "=" * 60)
    print(f"【测试4】重试分镜 (任务ID={task_id}, 分镜ID={scene_id})")
    print("=" * 60)
    
    try:
        response = requests.post(
            f"{BASE_URL}/tasks/{task_id}/scenes/{scene_id}/retry",
            params={"step_type": "image"}
        )
        if response.status_code == 200:
            data = response.json()
            print(f"✅ {data['message']}")
            return True
        else:
            print(f"❌ 重试失败: {response.status_code}")
            print(f"  错误: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return False


def test_retry_step(task_id):
    """测试重试任务步骤"""
    print("\n" + "=" * 60)
    print(f"【测试5】重试步骤 (任务ID={task_id})")
    print("=" * 60)
    
    try:
        response = requests.post(f"{BASE_URL}/tasks/{task_id}/steps/generate_images/retry")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ {data['message']}")
            return True
        else:
            print(f"❌ 重试失败: {response.status_code}")
            print(f"  错误: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return False


def main():
    print("\n🚀 开始测试任务管理 API")
    print("请确保 FastAPI 服务已启动 (python -m uvicorn app.main:app --reload)\n")
    
    # 测试1: 创建任务
    task_id = test_create_task()
    
    if task_id:
        # 测试2: 获取任务详情
        test_get_task_detail(task_id)
        
        # 测试3: 获取任务列表
        test_list_tasks()
        
        # 测试4: 重试分镜（需要有分镜ID）
        # test_retry_scene(task_id, 1)
        
        # 测试5: 重试步骤
        # test_retry_step(task_id)
    
    print("\n" + "=" * 60)
    print("✓ 测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()

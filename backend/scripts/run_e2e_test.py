import json
import os
import sys
import time

import requests

BACKEND_ROOT = os.path.dirname(os.path.dirname(__file__))
SRC_DIR = os.path.join(BACKEND_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from app.core.env import load_env  # type: ignore[import-not-found]

load_env()

API = os.getenv("API_BASE") or "http://localhost:8000"
HEADERS = {"Content-Type": "application/json"}

payload = {
    "title": "自动模式端到端测试",
    "description": "测试自动模式：storyboard->images->audio->video 自动串联",
    "task_config": {
        "scene_count": 2,
        "language": "中文"
    },
    "mode": "auto"
}

print('向 API 创建任务：', API + '/api/v1/tasks/')
resp = requests.post(f"{API}/api/v1/tasks/", json=payload, headers=HEADERS)
print('create_task ->', resp.status_code, resp.text)
if resp.status_code not in (200,201):
    raise SystemExit("创建任务失败，检查 API 日志或 DB")

task = resp.json()
task_id = task["id"]
print("任务 ID:", task_id)

# 简单轮询 steps 状态直到最后一个 step 完成或出错（超时 600s）
start = time.time()
timeout = 600
while time.time() - start < timeout:
    r = requests.get(f"{API}/api/v1/tasks/{task_id}", headers=HEADERS)
    if r.status_code != 200:
        print("无法获取任务详情:", r.status_code, r.text)
        break
    data = r.json()
    steps = data["steps"]
    print(time.strftime("%H:%M:%S"), "步骤状态：", [(s["step_name"], s["status"]) for s in steps])
    # 状态码: 0待处理,1处理中,2成功,3失败
    if any(s["status"] == 3 for s in steps):
        print("检测到步骤失败，详情：", steps)
        break
    if all(s["status"] == 2 for s in steps):
        print("所有步骤完成！")
        break
    time.sleep(5)
else:
    print("超时，任务未在限定时间内完成，请检查 worker 日志或数据库")

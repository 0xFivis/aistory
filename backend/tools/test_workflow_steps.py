import sys, traceback
sys.path.insert(0, r'D:\workspace\aistory\backend\src')

from app.services.workflow_service import WorkflowService
from app.services.gemini_service import GeminiService
from app.services.exceptions import ConfigurationException
from app.database import get_db_session

# We'll construct a minimal 'task' and 'step' like objects (duck typing) so we can call run_step synchronously
class SimpleTask:
    def __init__(self, params=None, task_config=None, mode='auto'):
        self.params = params or {}
        self.task_config = task_config or {}
        self.mode = mode

class SimpleStep:
    def __init__(self, step_name, params=None):
        self.step_name = step_name
        self.params = params or {}

# Create a real DB session so services can load credentials from service_credentials
db = None
try:
    db = get_db_session()
except Exception as e:
    print('Failed to obtain DB session:', e)

ws = WorkflowService(db=db)

steps = ["storyboard", "generate_images", "generate_audio", "generate_videos"]

print('Testing in auto mode')
task = SimpleTask(params={'description':'测试文案'}, task_config={'scene_count':3}, mode='auto')
for s in steps:
    step = SimpleStep(s)
    try:
        res = ws.run_step(task, step)
        print(f"Step {s} returned:", res)
        if task.mode == 'auto':
            print(f"[auto] 任务处于 auto 模式：将在真实运行中自动触发下一步骤({s} -> next)")
        else:
            print(f"[manual] 任务处于 manual 模式：不会自动触发下一步骤({s})")
    except ConfigurationException as ce:
        print(f"ConfigurationException at step {s}: {ce}")
    except Exception:
        traceback.print_exc()

print('\nTesting in manual mode')
task = SimpleTask(params={'description':'测试文案'}, task_config={'scene_count':3}, mode='manual')
for s in steps:
    step = SimpleStep(s)
    try:
        res = ws.run_step(task, step)
        print(f"Step {s} returned:", res)
        if task.mode == 'auto':
            print(f"[auto] 任务处于 auto 模式：将在真实运行中自动触发下一步骤({s} -> next)")
        else:
            print(f"[manual] 任务处于 manual 模式：不会自动触发下一步骤({s})")
    except ConfigurationException as ce:
        print(f"ConfigurationException at step {s}: {ce}")
    except Exception:
        traceback.print_exc()

if db:
    try:
        db.close()
    except Exception:
        pass

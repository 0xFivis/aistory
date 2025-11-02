import sys, traceback
sys.path.insert(0, r'D:\workspace\aistory\backend\src')

# 用假的服务替换真实服务，避免外部网络调用
from app import services as services_pkg

# Define fakes
class FakeGemini:
    def __init__(self, *args, **kwargs):
        pass

    @property
    def service_name(self):
        return 'Google Gemini (fake)'

    def generate_storyboard(self, video_content, reference_video=None, num_scenes=3, language='中文'):
        # return simple fake scenes
        scenes = []
        for i in range(1, num_scenes + 1):
            scenes.append({
                'scene_number': i,
                'narration': f'第{i}场旁白',
                'narration_word_count': 5,
                'image_prompt': f'prompt for scene {i}'
            })
        return scenes

class FakeLiblib:
    def __init__(self, *args, **kwargs):
        pass
    @property
    def service_name(self):
        return 'Liblib AI (fake)'
    def generate_image(self, prompt, **kwargs):
        return {'url': f'https://example.com/{hash(prompt) % 10000}.png', 'prompt': prompt}

class FakeFishAudio:
    def __init__(self, *args, **kwargs):
        pass
    @property
    def service_name(self):
        return 'Fish Audio (fake)'
    def text_to_speech(self, text, **kwargs):
        return b'FAKEAUDIO'

class FakeNCA:
    def __init__(self, *args, **kwargs):
        pass
    @property
    def service_name(self):
        return 'NCA Toolkit (fake)'
    def process_video(self, input_path, output_path, options=None):
        return {'stdout': 'ok', 'stderr': '', 'exit_code': 0}

# Monkeypatch real classes
import importlib
gemini_mod = importlib.import_module('app.services.gemini_service')
liblib_mod = importlib.import_module('app.services.liblib_service')
fishaudio_mod = importlib.import_module('app.services.fishaudio_service')
nca_mod = importlib.import_module('app.services.nca_service')

gemini_mod.GeminiService = FakeGemini
liblib_mod.LiblibService = FakeLiblib
fishaudio_mod.FishAudioService = FakeFishAudio
nca_mod.NCAService = FakeNCA

# Now run workflow
from app.services.workflow_service import WorkflowService

class SimpleTask:
    def __init__(self, params=None, task_config=None, mode='auto'):
        self.params = params or {}
        self.task_config = task_config or {}
        self.mode = mode

class SimpleStep:
    def __init__(self, step_name, params=None):
        self.step_name = step_name
        self.params = params or {}

steps = ['storyboard', 'generate_images', 'generate_audio', 'generate_videos']

print('==== 测试：auto 模式（应自动顺序执行所有步骤） ====')
try:
    ws = WorkflowService(db=None)
    task = SimpleTask(params={'description': '这是一个自动链路测试'}, task_config={'scene_count': 3}, mode='auto')
    current_idx = 0
    while current_idx < len(steps):
        step = SimpleStep(steps[current_idx])
        try:
            res = ws.run_step(task, step)
            print(f"步骤 {step.step_name} 返回: {res}")
        except Exception as e:
            print(f"步骤 {step.step_name} 抛出异常: {e}")
            break
        # auto 模式：继续下一步
        if task.mode == 'auto':
            current_idx += 1
        else:
            break
except Exception:
    traceback.print_exc()

print('\n==== 测试：manual 模式（只执行单步） ====')
try:
    ws = WorkflowService(db=None)
    task = SimpleTask(params={'description': '这是一个手动模式测试'}, task_config={'scene_count': 2}, mode='manual')
    # 仅执行 storyboard 这一步并停止
    step = SimpleStep('storyboard')
    try:
        res = ws.run_step(task, step)
        print(f"步骤 {step.step_name} 返回: {res}")
        print('手动模式：不会自动继续下一步')
    except Exception as e:
        print(f"步骤 {step.step_name} 抛出异常: {e}")
except Exception:
    traceback.print_exc()

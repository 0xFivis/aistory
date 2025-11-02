import sys, traceback
sys.path.insert(0, r'D:\workspace\aistory\backend\src')

from app.services.gemini_service import GeminiService

print('Instantiate and call GeminiService.generate_storyboard')
try:
    g = GeminiService()
    scenes = g.generate_storyboard('测试文案', num_scenes=3)
    print('Generated scenes:', scenes)
except Exception:
    traceback.print_exc()

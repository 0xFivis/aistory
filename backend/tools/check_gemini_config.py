import sys
sys.path.insert(0, r'D:\workspace\aistory\backend\src')
from app.config.settings import get_settings
s = get_settings()
print('GOOGLE_GEMINI_MODEL (effective):', repr(s.GOOGLE_GEMINI_MODEL))
# try resolved key
try:
    print('resolved_gemini_api_key (from DB):', repr(s.resolved_gemini_api_key))
except Exception as e:
    print('Error reading resolved_gemini_api_key:', e)

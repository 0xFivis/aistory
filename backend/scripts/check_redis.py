import os
import sys
from urllib.parse import urlparse

BACKEND_ROOT = os.path.dirname(os.path.dirname(__file__))
SRC_DIR = os.path.join(BACKEND_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from app.core.env import load_env  # type: ignore[import-not-found]

load_env()
redis_url = os.getenv('REDIS_URL') or os.getenv('CELERY_BROKER_URL')
print('使用的 REDIS URL:', redis_url)
if not redis_url:
    print('未配置 REDIS_URL')
    raise SystemExit(2)

u = urlparse(redis_url)
import redis
try:
    r = redis.Redis(host=u.hostname, port=u.port or 6379, db=int(u.path.lstrip('/') or '0'))
    r.ping()
    print('Redis 连接成功')
except Exception as e:
    print('Redis 连接失败:', e)
    raise

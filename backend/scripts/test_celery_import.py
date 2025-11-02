import sys
from pathlib import Path

backend_src = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(backend_src))

try:
    from app.celery_app import celery_app
    print("Celery app import: OK")
    # Eager test
    celery_app.conf.task_always_eager = True
    res = celery_app.send_task("example.add", args=[2, 3])
    print("Task result:", res.get())
    print("✓ Celery eager task executed")
except Exception as e:
    print("Celery app import: FAIL", e)

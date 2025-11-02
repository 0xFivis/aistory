import sys
from pathlib import Path

backend_src = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(backend_src))

try:
    from app.services.cloudinary_service import CloudinaryService
    svc = CloudinaryService()
    svc.ensure_configured()
    print("Cloudinary config: OK")
except Exception as e:
    print("Cloudinary config check: FAIL or not configured ->", e)

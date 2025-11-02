"""Static media file serving for generated assets."""
from __future__ import annotations

import mimetypes
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config.settings import get_settings

router = APIRouter(prefix="/api/v1/storage", tags=["Storage"])
_settings = get_settings()
if not _settings.STORAGE_BASE_PATH:
    raise RuntimeError("STORAGE_BASE_PATH is not configured")
_BASE_STORAGE_PATH = Path(_settings.STORAGE_BASE_PATH).resolve()


@router.get("/{resource_path:path}", summary="获取生成的媒体文件")
def serve_storage_file(resource_path: str):
    """Return a file stored under the configured storage directory."""
    if not resource_path:
        raise HTTPException(status_code=400, detail="文件路径不能为空")

    target_path = (_BASE_STORAGE_PATH / resource_path).resolve()

    # 防止目录穿越，确保仍位于 storage 目录下
    try:
        target_path.relative_to(_BASE_STORAGE_PATH)
    except ValueError as exc:  # pragma: no cover - defensive branch
        raise HTTPException(status_code=404, detail="文件不存在") from exc

    if not target_path.exists() or not target_path.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")

    media_type, _ = mimetypes.guess_type(str(target_path))
    return FileResponse(target_path, media_type=media_type or "application/octet-stream")

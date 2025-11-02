"""Audio generation provider implementations."""
from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.services.exceptions import ConfigurationException
from app.services.fishaudio_service import FishAudioService
from .base import AudioGenerationProvider, MediaRequest, MediaResult


class FishAudioProvider(AudioGenerationProvider):
    provider_name = "fishaudio"

    def __init__(self, db: Session) -> None:
        self._service = FishAudioService(db)
        self._settings = get_settings()

    def _ensure_storage_dir(self) -> Path:
        if not self._settings.STORAGE_BASE_PATH:
            raise ConfigurationException(
                "STORAGE_BASE_PATH is not configured",
                service_name=self.provider_name,
            )
        base = Path(self._settings.STORAGE_BASE_PATH).resolve()
        audio_dir = base / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        return audio_dir

    def _build_access_paths(self, file_path: Path) -> dict:
        if not self._settings.STORAGE_BASE_PATH:
            raise ConfigurationException(
                "STORAGE_BASE_PATH is not configured",
                service_name=self.provider_name,
            )

        base_dir = Path(self._settings.STORAGE_BASE_PATH).resolve()
        resolved_path = file_path.resolve()
        try:
            relative_path = resolved_path.relative_to(base_dir)
        except ValueError:
            relative_path = Path(resolved_path.name)

        relative_posix = relative_path.as_posix()
        api_path = f"/api/v1/storage/{relative_posix}"

        public_base = (self._settings.STORAGE_PUBLIC_BASE_URL or "").strip()
        public_url = None
        if public_base:
            public_url = f"{public_base.rstrip('/')}{api_path}"

        return {
            "relative_path": relative_posix,
            "api_path": api_path,
            "public_url": public_url,
        }

    def generate(self, request: MediaRequest) -> MediaResult:
        if not request.text:
            return MediaResult(status="failed", meta={"error": "text is empty"})

        extra = request.extra or {}
        fmt = extra.get("format") or "mp3"
        sample_rate = extra.get("sample_rate") or 44100
        audio_bytes = self._service.text_to_speech(
            text=request.text,
            voice_id=request.voice_id,
            format=fmt,
            sample_rate=sample_rate,
        )

        audio_dir = self._ensure_storage_dir()
        filename = extra.get("filename")
        if not filename:
            filename = f"{extra.get('task_id', 'task')}_{extra.get('scene_seq', 'scene')}.mp3"
        output_path = audio_dir / filename
        with open(output_path, "wb") as fh:
            fh.write(audio_bytes)

        access_info = self._build_access_paths(output_path)
        resource_url = access_info["api_path"]
        meta = {
            "storage": "local",
            "size": len(audio_bytes),
            "path": str(output_path),
            "relative_path": access_info["relative_path"],
            "api_path": access_info["api_path"],
            "public_url": access_info["public_url"],
            "format": fmt,
            "sample_rate": sample_rate,
        }

        return MediaResult(
            status="completed",
            resource_url=resource_url,
            meta=meta,
        )


__all__ = ["FishAudioProvider"]

"""Local storage helper for media assets."""
from __future__ import annotations

import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urljoin, urlparse

from fastapi import UploadFile

from app.config.settings import Settings, get_settings
from app.services.exceptions import ConfigurationException
from app.utils.timezone import naive_now

_API_STORAGE_PREFIX = "/api/v1/storage/"


@dataclass(frozen=True)
class StorageReference:
    """Describe a stored asset with multiple useful representations."""

    api_path: str
    relative_path: str
    absolute_path: Optional[Path]
    public_url: Optional[str]


@dataclass(frozen=True)
class StorageSaveResult:
    """Result of persisting an uploaded file to local storage."""

    relative_path: str  # Path relative to STORAGE_BASE_PATH (e.g. "audio/foo.mp3")
    api_path: str  # API path that can be persisted to DB (e.g. "/api/v1/storage/audio/foo.mp3")
    absolute_path: Path
    file_size: int
    content_type: Optional[str]


class StorageService:
    """Encapsulates media storage operations (save + resolve URLs)."""

    def __init__(self, settings: Optional[Settings] = None):
        self._settings = settings or get_settings()
        if not self._settings.STORAGE_BASE_PATH:
            raise ConfigurationException("STORAGE_BASE_PATH is not configured", service_name="StorageService")
        self._base_path = Path(self._settings.STORAGE_BASE_PATH).resolve()
        public_base = (self._settings.STORAGE_PUBLIC_BASE_URL or "").strip()
        self._public_base_url = public_base.rstrip("/") if public_base else ""

    def _category_dir(self, asset_type: Optional[str]) -> Path:
        type_map = {
            "bgm": "audio",
            "music": "audio",
            "audio": "audio",
            "voice": "audio",
            "image": "images",
            "picture": "images",
            "cover": "images",
            "video": "video",
            "template": "templates",
        }
        key = (asset_type or "misc").strip().lower()
        sub_dir = type_map.get(key, key or "misc")
        return self._base_path / sub_dir

    def save_upload(self, asset_type: str, upload: UploadFile) -> StorageSaveResult:
        """Persist an uploaded file, returning paths suitable for DB storage."""

        target_dir = self._category_dir(asset_type)
        target_dir.mkdir(parents=True, exist_ok=True)

        suffix = Path(upload.filename or "").suffix.lower()
        token = secrets.token_hex(8)
        timestamp = naive_now().strftime("%Y%m%d%H%M%S")
        filename = f"{timestamp}_{token}{suffix}"
        absolute_path = target_dir / filename

        file_size = 0
        with absolute_path.open("wb") as buffer:
            while True:
                chunk = upload.file.read(1024 * 1024)
                if not chunk:
                    break
                buffer.write(chunk)
                file_size += len(chunk)

        # Reset pointer in case caller wants to re-use the file
        try:
            upload.file.seek(0)
        except Exception:  # pragma: no cover - best effort
            pass

        relative_path = absolute_path.relative_to(self._base_path).as_posix()
        api_path = f"{_API_STORAGE_PREFIX}{relative_path}".replace("//", "/")

        return StorageSaveResult(
            relative_path=relative_path,
            api_path=api_path if api_path.startswith("/") else f"/{api_path}",
            absolute_path=absolute_path,
            file_size=file_size,
            content_type=upload.content_type,
        )

    def save_text(
        self,
        asset_type: str,
        content: str,
        *,
        suffix: str = ".txt",
        encoding: str = "utf-8",
    ) -> StorageReference:
        """Persist text content into storage and return a reference."""

        target_dir = self._category_dir(asset_type)
        target_dir.mkdir(parents=True, exist_ok=True)

        timestamp = naive_now().strftime("%Y%m%d%H%M%S")
        token = secrets.token_hex(8)
        filename = f"{timestamp}_{token}{suffix}"
        absolute_path = target_dir / filename
        absolute_path.write_text(content, encoding=encoding)

        return self.reference_from_absolute(absolute_path)

    def ensure_api_path(self, value: str) -> str:
        """Normalise an input path to `/api/v1/storage/...` (reject absolute URLs)."""

        if not value:
            raise ValueError("file path cannot be empty")

        value = value.strip().replace("\\", "/")

        if value.startswith(_API_STORAGE_PREFIX):
            return value

        parsed = urlparse(value)
        if parsed.scheme in {"http", "https"}:
            # Require callers to provide relative API path to avoid host lock-in
            value = parsed.path or ""
            if value.startswith(_API_STORAGE_PREFIX):
                return value

        if not value:
            raise ValueError("file path cannot be empty")

        path_candidate = Path(value)
        if path_candidate.is_absolute():
            try:
                relative = path_candidate.resolve().relative_to(self._base_path).as_posix()
            except ValueError as exc:
                raise ValueError("absolute path is outside of storage base path") from exc
            return (
                _API_STORAGE_PREFIX.rstrip("/")
                if not relative
                else f"{_API_STORAGE_PREFIX}{relative}"
            )

        if value.startswith("/"):
            value = value[1:]
        if value.startswith(_API_STORAGE_PREFIX.lstrip("/")):
            return f"/{value}"
        return f"{_API_STORAGE_PREFIX}{value}" if value else _API_STORAGE_PREFIX.rstrip("/")

    def build_full_url(self, api_path: Optional[str]) -> Optional[str]:
        """Join configured public base URL with the API path (if provided)."""

        if not api_path:
            return None
        path = api_path.strip()
        if not path:
            return None
        if path.startswith("http://") or path.startswith("https://"):
            return path
        base = self._public_base_url
        if not base:
            return path if path.startswith("/") else f"/{path}"
        return urljoin(f"{base}/", path.lstrip("/"))

    def to_absolute_path(self, api_path: str) -> Path:
        """Translate an API path back to a file on disk."""

        if not api_path:
            raise ValueError("api_path cannot be empty")
        parsed = urlparse(api_path)
        if parsed.scheme in {"http", "https"}:
            raise ValueError("cannot convert remote URL to local path")
        value = api_path.replace(_API_STORAGE_PREFIX, "", 1).strip("/")
        if not value and api_path.startswith(_API_STORAGE_PREFIX):
            value = ""
        path = value
        candidate = (self._base_path / path).resolve()
        candidate.relative_to(self._base_path)  # ensure within base path
        return candidate

    def reference_from_absolute(self, absolute_path: Path) -> StorageReference:
        resolved = absolute_path.resolve()
        relative_path = resolved.relative_to(self._base_path).as_posix()
        api_path = f"{_API_STORAGE_PREFIX}{relative_path}"
        public_url = self.build_full_url(api_path)
        return StorageReference(
            api_path=api_path,
            relative_path=relative_path,
            absolute_path=resolved,
            public_url=public_url,
        )

    def resolve_reference(self, value: Optional[str]) -> Optional[StorageReference]:
        if value is None:
            return None
        raw = str(value).strip()
        if not raw:
            return None
        if raw.startswith("http://") or raw.startswith("https://"):
            return StorageReference(
                api_path=raw,
                relative_path="",
                absolute_path=None,
                public_url=raw,
            )

        try:
            api_path = self.ensure_api_path(raw)
        except ValueError:
            return None

        absolute = self.to_absolute_path(api_path)
        relative = absolute.relative_to(self._base_path).as_posix()
        public_url = self.build_full_url(api_path)
        return StorageReference(
            api_path=api_path,
            relative_path=relative,
            absolute_path=absolute,
            public_url=public_url,
        )

    def ensure_local_path(self, value: str) -> Path:
        reference = self.resolve_reference(value)
        if reference and reference.absolute_path:
            return reference.absolute_path
        # value might already be an absolute filesystem path
        path_candidate = Path(value)
        if path_candidate.is_absolute():
            return path_candidate
        raise ValueError(f"unable to resolve local path for value: {value}")

    def get_external_url(self, value: Optional[str]) -> Optional[str]:
        """Return an externally accessible URL for stored assets (if available)."""

        reference = self.resolve_reference(value)
        if reference:
            return reference.public_url or reference.api_path
        return None

    def describe_reference(self, value: Optional[str]) -> Optional[Dict[str, Optional[str]]]:
        """Provide a structured description for API responses (api path + external url)."""

        reference = self.resolve_reference(value)
        if not reference:
            return None
        relative_path = reference.relative_path or None
        return {
            "api_path": reference.api_path,
            "relative_path": relative_path,
            "public_url": reference.public_url or reference.api_path,
        }
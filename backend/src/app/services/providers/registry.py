"""Provider registry for workflow feature modules."""
from __future__ import annotations

from typing import Dict, Type, Optional
from sqlalchemy.orm import Session

from .base import (
    StoryboardProvider,
    StoryboardRequest,
    StoryboardResult,
    ImageGenerationProvider,
    AudioGenerationProvider,
    VideoGenerationProvider,
    VideoPromptProvider,
    MediaComposeProvider,
)
from app.config.settings import get_settings
from .storyboard import GeminiStoryboardProvider
from .image import LiblibImageProvider, ComfyUIImageProvider, RunningHubImageProvider
from .audio import FishAudioProvider
from .video import NcaVideoProvider, FalVideoProvider, RunningHubVideoProvider
from .video_prompt import GeminiVideoPromptProvider
from .compose import NcaComposeProvider, FfmpegComposeProvider

_settings = get_settings()
DEFAULT_PROVIDERS: Dict[str, str] = dict(_settings.provider_defaults)

_PROVIDER_MAP: Dict[str, Dict[str, Type]] = {
    "storyboard": {
        "gemini": GeminiStoryboardProvider,
    },
    "image": {
        "liblib": LiblibImageProvider,
        "comfyui": ComfyUIImageProvider,
        "runninghub": RunningHubImageProvider,
    },
    "audio": {
        "fishaudio": FishAudioProvider,
    },
    "video": {
        "nca": NcaVideoProvider,
        "fal": FalVideoProvider,
        "runninghub": RunningHubVideoProvider,
    },
    "video_prompt": {
        "gemini": GeminiVideoPromptProvider,
    },
    "media_compose": {
        "nca": NcaComposeProvider,
        "ffmpeg": FfmpegComposeProvider,
    },
}


def _resolve_provider_class(feature: str, provider_name: str) -> Type:
    feature_map = _PROVIDER_MAP.get(feature)
    if not feature_map or provider_name not in feature_map:
        raise ValueError(f"Provider '{provider_name}' not registered for feature '{feature}'")
    return feature_map[provider_name]


def get_provider(feature: str, provider_name: str, db: Session):
    provider_cls = _resolve_provider_class(feature, provider_name)
    try:
        return provider_cls(db)
    except TypeError:
        return provider_cls()  # Some providers may not require DB


def resolve_task_provider(feature: str, task_providers: Optional[Dict[str, str]], db: Session):
    provider_name = (task_providers or {}).get(feature) or DEFAULT_PROVIDERS.get(feature)
    if not provider_name:
        raise ValueError(f"No default provider configured for feature '{feature}'")
    return get_provider(feature, provider_name, db), provider_name


__all__ = ["DEFAULT_PROVIDERS", "resolve_task_provider"]

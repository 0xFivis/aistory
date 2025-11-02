"""Provider base classes and data contracts for workflow modules."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod


# ---- Storyboard generation ----

@dataclass
class StoryboardRequest:
    video_content: str
    scene_count: int
    language: str
    reference_video: Optional[str] = None
    word_count_strategy: Optional[str] = None
    prompt_example: Optional[str] = None
    trigger_words: Optional[str] = None
    channel_identity: Optional[str] = None


@dataclass
class StoryboardScene:
    scene_number: int
    narration: str
    narration_word_count: int
    image_prompt: str


@dataclass
class StoryboardResult:
    scenes: List[StoryboardScene]
    raw: Optional[Any] = None


class StoryboardProvider(ABC):
    feature_name = "storyboard"
    provider_name: str

    @abstractmethod
    def generate(self, request: StoryboardRequest) -> StoryboardResult:
        raise NotImplementedError


# ---- Generic media generation ----

@dataclass
class MediaRequest:
    prompt: Optional[str] = None
    negative_prompt: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    text: Optional[str] = None
    voice_id: Optional[str] = None
    image_url: Optional[str] = None
    audio_url: Optional[str] = None
    duration: Optional[float] = None
    extra: Optional[Dict[str, Any]] = None


@dataclass
class MediaResult:
    status: str  # "completed" | "queued" | "failed"
    resource_url: Optional[str] = None
    job_id: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


class MediaProvider(ABC):
    feature_name: str
    provider_name: str

    @abstractmethod
    def generate(self, request: MediaRequest) -> MediaResult:
        raise NotImplementedError


class ImageGenerationProvider(MediaProvider):
    feature_name = "image"


class AudioGenerationProvider(MediaProvider):
    feature_name = "audio"


class VideoGenerationProvider(MediaProvider):
    feature_name = "video"


@dataclass
class VideoPromptRequest:
    scene_seq: int
    narration: str
    image_prompt: Optional[str] = None
    image_url: Optional[str] = None
    storyboard_context: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None


@dataclass
class VideoPromptResult:
    prompt: str
    raw: Optional[Any] = None


class VideoPromptProvider(ABC):
    feature_name = "video_prompt"
    provider_name: str

    @abstractmethod
    def generate(self, request: VideoPromptRequest) -> VideoPromptResult:
        raise NotImplementedError


@dataclass
class ComposeInput:
    image_url: Optional[str] = None
    audio_url: Optional[str] = None
    video_url: Optional[str] = None
    caption: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    extra: Optional[Dict[str, Any]] = None


@dataclass
class ComposeRequest:
    clips: List[ComposeInput]
    output_format: Optional[str] = None
    resolution: Optional[str] = None
    frame_rate: Optional[int] = None
    audio_bitrate: Optional[int] = None
    video_bitrate: Optional[int] = None
    extra: Optional[Dict[str, Any]] = None


@dataclass
class ComposeResult:
    status: str
    video_url: Optional[str] = None
    job_id: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


class MediaComposeProvider(MediaProvider):
    feature_name = "media_compose"

    @abstractmethod
    def compose(self, request: ComposeRequest) -> ComposeResult:
        raise NotImplementedError

    # Backward compatibility for subclasses using `generate`
    def generate(self, request: MediaRequest) -> MediaResult:  # pragma: no cover - bridge method
        compose_request = None
        if request.extra and isinstance(request.extra.get("compose_request"), ComposeRequest):
            compose_request = request.extra["compose_request"]

        if not compose_request:
            raise NotImplementedError("Provide ComposeRequest via MediaRequest.extra['compose_request']")

        result = self.compose(compose_request)
        return MediaResult(
            status=result.status,
            resource_url=result.video_url,
            job_id=result.job_id,
            meta=result.meta,
        )


__all__ = [
    "StoryboardRequest",
    "StoryboardScene",
    "StoryboardResult",
    "StoryboardProvider",
    "ComposeInput",
    "ComposeRequest",
    "ComposeResult",
    "MediaRequest",
    "MediaResult",
    "ImageGenerationProvider",
    "AudioGenerationProvider",
    "VideoGenerationProvider",
    "VideoPromptRequest",
    "VideoPromptResult",
    "VideoPromptProvider",
    "MediaComposeProvider",
]

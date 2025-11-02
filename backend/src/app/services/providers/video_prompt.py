"""Video prompt provider implementations."""
from __future__ import annotations

from typing import Optional
from sqlalchemy.orm import Session

from app.services.gemini_service import GeminiService
from .base import VideoPromptProvider, VideoPromptRequest, VideoPromptResult


class GeminiVideoPromptProvider(VideoPromptProvider):
    provider_name = "gemini"

    def __init__(self, db: Optional[Session] = None) -> None:
        # GeminiService manages its own credential lookup from the settings layer
        self._service = GeminiService()

    def generate(self, request: VideoPromptRequest) -> VideoPromptResult:
        extra = request.extra or {}
        target_provider = extra.get("target_provider") or extra.get("video_provider") or ""
        duration_hint = extra.get("duration") or extra.get("video_duration")

        response = self._service.generate_video_prompt(
            target=target_provider,
            narration=request.narration,
            scene_seq=request.scene_seq,
            image_prompt=request.image_prompt,
            image_url=request.image_url,
            storyboard_context=request.storyboard_context,
            duration_hint=duration_hint,
        )
        return VideoPromptResult(prompt=response.get("prompt", ""), raw=response)


__all__ = ["GeminiVideoPromptProvider"]

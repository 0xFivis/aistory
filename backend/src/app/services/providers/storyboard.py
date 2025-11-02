"""Storyboard provider implementations."""
from __future__ import annotations

from typing import Optional
from sqlalchemy.orm import Session

from app.services.gemini_service import GeminiService
from .base import (
    StoryboardProvider,
    StoryboardRequest,
    StoryboardResult,
    StoryboardScene,
)


class GeminiStoryboardProvider(StoryboardProvider):
    provider_name = "gemini"

    def __init__(self, db: Optional[Session] = None) -> None:
        # GeminiService currently handles its own DB access for credentials
        self._service = GeminiService()

    def generate(self, request: StoryboardRequest) -> StoryboardResult:
        scenes = self._service.generate_storyboard(
            video_content=request.video_content,
            reference_video=request.reference_video,
            num_scenes=request.scene_count,
            language=request.language,
            word_count_strategy=request.word_count_strategy,
            prompt_example=request.prompt_example,
            trigger_words=request.trigger_words,
            channel_identity=request.channel_identity,
        )
        parsed = [
            StoryboardScene(
                scene_number=item.get("scene_number", idx + 1),
                narration=item.get("narration", ""),
                narration_word_count=item.get(
                    "narration_word_count", len(item.get("narration", ""))
                ),
                image_prompt=item.get("image_prompt", ""),
            )
            for idx, item in enumerate(scenes)
        ]
        return StoryboardResult(scenes=parsed, raw=scenes)


__all__ = ["GeminiStoryboardProvider"]

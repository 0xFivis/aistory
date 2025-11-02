"""Media composition provider implementations."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.services.nca_service import NCAService
from app.services.ffmpeg_service import FFmpegService
from .base import (
    ComposeInput,
    ComposeRequest,
    ComposeResult,
    MediaComposeProvider,
)


class NcaComposeProvider(MediaComposeProvider):
    provider_name = "nca"

    def __init__(self, db: Session) -> None:
        self._service = NCAService(db)

    def compose(self, request: ComposeRequest) -> ComposeResult:
        payload = self._build_payload(request)
        timeout = None
        if request.extra and isinstance(request.extra.get("timeout"), (int, float)):
            timeout = int(request.extra["timeout"])

        try:
            response = self._service.compose(payload, timeout=timeout)
        except Exception as exc:  # pragma: no cover - remote failure
            return ComposeResult(status="failed", meta={"error": str(exc)})

        meta = response if isinstance(response, dict) else {"raw": response}
        video_url: Optional[str] = None
        job_id: Optional[str] = None
        status = "failed"

        if isinstance(response, dict):
            video_url = response.get("video_url") or response.get("url")
            job_id = response.get("job_id") or response.get("task_id")
            status = response.get("status") or response.get("state") or status

            data = response.get("data")
            if isinstance(data, dict):
                video_url = video_url or data.get("video_url") or data.get("url")
                job_id = job_id or data.get("job_id") or data.get("task_id")
                status = data.get("status") or data.get("state") or status

        if video_url:
            resolved_url = self._service.resolve_media_url(video_url)
            return ComposeResult(
                status="completed",
                video_url=resolved_url or video_url,
                job_id=job_id,
                meta=meta,
            )

        if job_id and status not in ("failed", "error"):
            return ComposeResult(status="queued", job_id=job_id, meta=meta)

        return ComposeResult(status=status or "failed", job_id=job_id, meta=meta)

    def _build_payload(self, request: ComposeRequest) -> Dict[str, Any]:
        extra = request.extra or {}
        if "compose_payload" in extra and isinstance(extra["compose_payload"], dict):
            base_payload = dict(extra["compose_payload"])
        else:
            base_payload = {
                "clips": self._build_clips(request.clips),
            }

        output = base_payload.setdefault("output", {})
        if request.output_format:
            output.setdefault("format", request.output_format)
        if request.resolution:
            output.setdefault("resolution", request.resolution)
        if request.frame_rate is not None:
            output.setdefault("frame_rate", request.frame_rate)
        if request.audio_bitrate is not None:
            output.setdefault("audio_bitrate", request.audio_bitrate)
        if request.video_bitrate is not None:
            output.setdefault("video_bitrate", request.video_bitrate)

        # Merge extra output overrides if provided via extra
        if isinstance(extra.get("output"), dict):
            output.update({k: v for k, v in extra["output"].items() if v is not None})

        # Attach any additional compose params
        if isinstance(extra.get("options"), dict):
            base_payload.setdefault("options", {}).update(extra["options"])

        return base_payload

    def _build_clips(self, clips: List[ComposeInput]) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
        for clip in clips:
            clip_payload: Dict[str, Any] = {}
            if clip.video_url:
                clip_payload["video_url"] = clip.video_url
            if clip.image_url:
                clip_payload["image_url"] = clip.image_url
            if clip.audio_url:
                clip_payload["audio_url"] = clip.audio_url
            if clip.caption:
                clip_payload["caption"] = clip.caption
            if clip.start_time is not None:
                clip_payload["start_time"] = clip.start_time
            if clip.end_time is not None:
                clip_payload["end_time"] = clip.end_time
            if clip.extra:
                clip_payload.update({k: v for k, v in clip.extra.items() if v is not None})

            if clip_payload:
                result.append(clip_payload)

        return result


class FfmpegComposeProvider(MediaComposeProvider):
    provider_name = "ffmpeg"

    def __init__(self, db: Optional[Session] = None) -> None:  # pylint: disable=unused-argument
        self._service = FFmpegService()

    def compose(self, request: ComposeRequest) -> ComposeResult:
        payload = None
        if request.extra and isinstance(request.extra.get("compose_payload"), dict):
            payload = request.extra["compose_payload"]

        if not payload:
            return ComposeResult(status="failed", meta={"error": "missing compose payload"})

        try:
            result = self._service.concat_with_payload(payload)
        except Exception as exc:  # pragma: no cover - subprocess failures
            return ComposeResult(status="failed", meta={"error": str(exc)})

        video_api_path = result.get("video_api_path") or result.get("video_url")
        return ComposeResult(
            status="completed",
            video_url=video_api_path,
            meta=result,
        )


__all__ = ["NcaComposeProvider", "FfmpegComposeProvider"]

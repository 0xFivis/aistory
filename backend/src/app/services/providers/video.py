"""Video generation provider implementations."""
from __future__ import annotations

import time
import logging
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.services.fal_service import FalService
from app.services.nca_service import NCAService
from app.services.runninghub_config import (
    DEFAULT_VIDEO_WORKFLOW_CONFIG,
    RunningHubWorkflowConfig,
    get_runninghub_config,
)
from app.models.concurrency import ServiceConcurrencySlot
from app.services.concurrency_manager import concurrency_manager
from app.services.runninghub_service import RunningHubService
from .base import MediaRequest, MediaResult, VideoGenerationProvider


class NcaVideoProvider(VideoGenerationProvider):
    provider_name = "nca"

    def __init__(self, db: Session) -> None:
        self._service = NCAService(db)

    def generate(self, request: MediaRequest) -> MediaResult:
        if not request.image_url:
            return MediaResult(status="failed", meta={"error": "image_url is required"})

        duration = max(1, int((request.duration or 5)))
        frame_rate = int((request.extra or {}).get("frame_rate", 25))
        try:
            response = self._service.image_to_video(
                image_url=request.image_url,
                length=duration,
                frame_rate=frame_rate,
                **((request.extra or {}).get("nca_options") or {}),
            )
        except Exception as exc:  # pragma: no cover - remote failure
            return MediaResult(status="failed", meta={"error": str(exc)})

        meta = response if isinstance(response, dict) else {"raw": response}
        video_url: Optional[str] = None
        job_id: Optional[str] = None

        if isinstance(response, dict):
            video_url = response.get("video_url") or response.get("url")
            job_id = response.get("job_id") or response.get("task_id")

        if video_url:
            resolved_url = self._service.resolve_media_url(video_url)
            return MediaResult(
                status="completed",
                resource_url=resolved_url or video_url,
                job_id=job_id,
                meta=meta,
            )

        if job_id:
            return MediaResult(status="queued", job_id=job_id, meta=meta)

        return MediaResult(status="failed", meta=meta)


class FalVideoProvider(VideoGenerationProvider):
    provider_name = "fal"

    def __init__(self, db: Optional[Session] = None) -> None:
        # FalService handles DB lookup internally when needed
        self._service = FalService()

    def generate(self, request: MediaRequest) -> MediaResult:
        if not request.image_url:
            return MediaResult(status="failed", meta={"error": "image_url is required"})

        raw_extra = request.extra
        extra: Dict[str, Any] = raw_extra if isinstance(raw_extra, dict) else {}
        prompt = (request.prompt or extra.get("prompt") or "").strip()
        if not prompt:
            return MediaResult(status="failed", meta={"error": "prompt is required"})

        duration = int(extra.get("duration") or request.duration or 6)
        try:
            response = self._service.image_to_video(
                image_url=request.image_url,
                prompt=prompt,
                duration=duration,
            )
        except Exception as exc:  # pragma: no cover - remote failure
            return MediaResult(status="failed", meta={"error": str(exc)})

        meta = response if isinstance(response, dict) else {"raw": response}
        video_url: Optional[str] = None
        job_id: Optional[str] = None

        if isinstance(response, dict):
            video_url = response.get("video_url") or response.get("url")
            job_id = response.get("job_id") or response.get("task_id")

            data = response.get("data")
            if not video_url and isinstance(data, dict):
                video_url = data.get("video_url") or data.get("url")
                job_id = job_id or data.get("job_id") or data.get("task_id")

        if video_url:
            return MediaResult(status="completed", resource_url=video_url, job_id=job_id, meta=meta)

        if job_id:
            return MediaResult(status="queued", job_id=job_id, meta=meta)

        return MediaResult(status="failed", meta=meta)


logger = logging.getLogger(__name__)


class RunningHubVideoProvider(VideoGenerationProvider):
    provider_name = "runninghub"

    WORKFLOW_ID = "1950150331004010497"
    INSTANCE_TYPE = "plus"
    MIN_DURATION = 2
    MAX_DURATION = 8
    DEFAULT_POLL_ATTEMPTS = 6
    DEFAULT_POLL_INTERVAL = 60.0
    DEFAULT_INITIAL_DELAY = 60.0
    DEFAULT_BUSY_WAIT = 10.0
    DEFAULT_CREATE_ATTEMPTS = 3

    def __init__(self, db: Session) -> None:
        self._db = db
        self._service = RunningHubService(db)
        self._default_config = get_runninghub_config(
            key="video.default",
            db=db,
            fallback=DEFAULT_VIDEO_WORKFLOW_CONFIG,
        )

    def _parse_int(self, value, default: int) -> int:
        try:
            return int(round(float(value)))
        except (TypeError, ValueError):
            return default

    def _parse_float(self, value, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _resolve_prompt(self, request: MediaRequest) -> Optional[str]:
        prompt = (request.prompt or "").strip()
        if prompt:
            return prompt
        extra = request.extra or {}
        prompt = (extra.get("prompt") or extra.get("video_prompt") or "").strip()
        if prompt:
            return prompt
        task_id = extra.get("task_id")
        scene_seq = extra.get("scene_seq")
        if task_id is None or scene_seq is None:
            return None
        try:
            from app.models.media import Scene  # Local import to avoid circular deps

            scene = (
                self._db.query(Scene)
                .filter(Scene.task_id == int(task_id), Scene.seq == int(scene_seq))
                .first()
            )
        except Exception:
            scene = None
        if scene is None:
            return None
        if isinstance(scene.video_meta, dict):
            prompt_candidate = (scene.video_meta.get("prompt") or "").strip()
            if prompt_candidate:
                return prompt_candidate
        if scene.image_prompt:
            return scene.image_prompt.strip()
        return None

    def generate(self, request: MediaRequest) -> MediaResult:
        if not request.image_url:
            return MediaResult(status="failed", meta={"error": "image_url is required"})

        prompt = self._resolve_prompt(request)
        if not prompt:
            return MediaResult(status="failed", meta={"error": "prompt is required"})

        raw_extra = request.extra
        extra: Dict[str, Any] = raw_extra if isinstance(raw_extra, dict) else {}
        config = self._resolve_config(extra)

        workflow_id = str(
            extra.get("runninghub_workflow_id")
            or config.workflow_id
            or self.WORKFLOW_ID
        )
        instance_type = str(
            extra.get("runninghub_instance_type")
            or config.instance_type
            or self.INSTANCE_TYPE
        )

        duration_value = request.duration
        if duration_value is None:
            duration_value = extra.get("duration") or extra.get("video_duration")
        min_duration = int(config.resolve_default("min_duration", self.MIN_DURATION))
        max_duration = int(config.resolve_default("max_duration", self.MAX_DURATION))
        duration = self._parse_int(duration_value, min_duration)
        duration = max(min_duration, min(max_duration, duration))

        node_info_list = extra.get("runninghub_node_info_list")
        if not node_info_list:
            default_node_113 = config.resolve_default("node_113", 2)
            default_node_153 = config.resolve_default("node_153", 2)
            default_node_247 = config.resolve_default("node_247", 4)
            default_node_272 = config.resolve_default("node_272", 2)
            selector_113 = self._parse_int(extra.get("runninghub_node_113", default_node_113), default_node_113)
            selector_153 = self._parse_int(extra.get("runninghub_node_153", default_node_153), default_node_153)
            selector_247 = self._parse_int(extra.get("runninghub_node_247", default_node_247), default_node_247)
            selector_272 = self._parse_int(extra.get("runninghub_node_272", default_node_272), default_node_272)
            context = {
                "prompt": prompt,
                "image_url": request.image_url,
                "duration": duration,
                "node_113": selector_113,
                "node_153": selector_153,
                "node_247": selector_247,
                "node_272": selector_272,
            }
            for key, value in config.defaults.items():
                context.setdefault(key, value)
            node_info_list = config.render_node_info(context)

        meta: Dict[str, Any] = {
            "workflow_id": workflow_id,
            "instance_type": instance_type,
            "config_key": config.key,
            "request": {
                "prompt": prompt,
                "image_url": request.image_url,
                "duration": duration,
            },
        }
        create_attempts = self._parse_int(
            extra.get("runninghub_create_attempts"),
            config.resolve_default("create_attempts", self.DEFAULT_CREATE_ATTEMPTS),
        )
        busy_wait = self._parse_float(
            extra.get("runninghub_busy_wait"),
            config.resolve_default("busy_wait", self.DEFAULT_BUSY_WAIT),
        )
        poll_attempts = self._parse_int(
            extra.get("runninghub_poll_attempts"),
            config.resolve_default("poll_attempts", self.DEFAULT_POLL_ATTEMPTS),
        )
        poll_interval = self._parse_float(
            extra.get("runninghub_poll_interval"),
            config.resolve_default("poll_interval", self.DEFAULT_POLL_INTERVAL),
        )
        initial_delay = self._parse_float(
            extra.get("runninghub_initial_delay"),
            config.resolve_default("initial_delay", self.DEFAULT_INITIAL_DELAY),
        )

        meta["poll_attempts"] = poll_attempts
        meta["poll_interval"] = poll_interval

        create_response: Optional[Dict[str, Any]] = None
        status: str = "pending"
        output_payload: Optional[Dict[str, Any]] = None

        token = concurrency_manager.acquire(
            "runninghub",
            feature="video",
            resource_id=self._build_resource_id(request),
            metadata={
                "task_id": extra.get("task_id"),
                "scene_seq": extra.get("scene_seq"),
                "feature": "video",
                "provider": "runninghub",
            },
        )

        release_status = ServiceConcurrencySlot.STATUS_RELEASED
        release_meta: Dict[str, Any] = {}

        try:
            for attempt in range(max(1, create_attempts)):
                create_response = self._service.create_task(
                    workflow_id=workflow_id,
                    node_info_list=node_info_list,
                    instance_type=instance_type,
                )
                meta["create_response"] = create_response

                if self._service.is_success_payload(create_response):
                    break

                if self._service.is_concurrency_limited(create_response):
                    if attempt < create_attempts - 1:
                        time.sleep(busy_wait)
                        continue
                    meta["error"] = (
                        self._service.extract_error_message(create_response)
                        or "Runninghub 并发配额不足"
                    )
                    release_status = ServiceConcurrencySlot.STATUS_ERROR
                    release_meta = {"reason": "concurrency_limited"}
                    return MediaResult(status="failed", meta=meta)

                meta["error"] = (
                    self._service.extract_error_message(create_response)
                    or "Runninghub 创建任务失败"
                )
                release_status = ServiceConcurrencySlot.STATUS_ERROR
                release_meta = {"reason": "create_failed"}
                return MediaResult(status="failed", meta=meta)

            task_id = self._service.extract_task_id(create_response)
            if not task_id:
                meta["error"] = (
                    self._service.extract_error_message(create_response)
                    or "Runninghub 响应缺少 taskId"
                )
                release_status = ServiceConcurrencySlot.STATUS_ERROR
                release_meta = {"reason": "missing_task_id"}
                return MediaResult(status="failed", meta=meta)

            meta["task_id"] = task_id
            concurrency_manager.update_metadata(token, {"task_id": task_id})

            if poll_attempts <= 0:
                release_status = ServiceConcurrencySlot.STATUS_RELEASED
                release_meta = {"job_id": task_id, "status": "queued"}
                return MediaResult(status="queued", job_id=task_id, meta=meta)

            status, output_payload = self._service.wait_for_task(
                task_id,
                max_attempts=poll_attempts,
                interval_seconds=poll_interval,
                initial_delay_seconds=initial_delay,
            )
            meta["last_output"] = output_payload

            if status == "success":
                entries = self._service.extract_file_entries(output_payload)
                video_url = None
                if entries:
                    first = entries[0]
                    video_url = (
                        first.get("fileUrl")
                        or first.get("file_url")
                        or first.get("url")
                        or first.get("value")
                    )
                if video_url:
                    meta["entries"] = entries
                    release_status = ServiceConcurrencySlot.STATUS_RELEASED
                    release_meta = {"job_id": task_id, "status": "completed"}
                    return MediaResult(status="completed", resource_url=video_url, job_id=task_id, meta=meta)
                meta["error"] = "Runninghub success response missing file URL"
                release_status = ServiceConcurrencySlot.STATUS_ERROR
                release_meta = {"job_id": task_id, "status": "invalid_output"}
                return MediaResult(status="failed", job_id=task_id, meta=meta)

            if status == "pending":
                meta.setdefault("error", "Runninghub 轮询超出最大次数")
                meta["timeout"] = True
                meta["timeout_attempts"] = poll_attempts
                release_status = ServiceConcurrencySlot.STATUS_TIMEOUT
                release_meta = {"job_id": task_id, "status": "timeout"}
                return MediaResult(status="failed", job_id=task_id, meta=meta)

            meta["error"] = self._service.extract_error_message(output_payload) or "Runninghub task failed"
            release_status = ServiceConcurrencySlot.STATUS_ERROR
            release_meta = {"job_id": task_id, "status": "failed"}
            return MediaResult(status="failed", job_id=task_id, meta=meta)
        except Exception as exc:
            release_status = ServiceConcurrencySlot.STATUS_ERROR
            release_meta = {"exception": str(exc)}
            raise
        finally:
            concurrency_manager.release(token, status=release_status, metadata=release_meta)

    @staticmethod
    def _build_resource_id(request: MediaRequest) -> str:
        extra = request.extra or {}
        task_id = extra.get("task_id") if isinstance(extra, dict) else None
        scene_seq = extra.get("scene_seq") if isinstance(extra, dict) else None
        if task_id is not None and scene_seq is not None:
            return f"task-{task_id}-scene-{scene_seq}-video"
        if task_id is not None:
            return f"task-{task_id}-video"
        if scene_seq is not None:
            return f"scene-{scene_seq}-video"
        return f"video-{int(time.time() * 1000)}"

    def _resolve_config(self, extra: Dict[str, Any]) -> RunningHubWorkflowConfig:
        config_id = extra.get("runninghub_video_workflow_config_id")
        if config_id is None:
            config_id = extra.get("runninghub_workflow_config_id")

        try:
            return get_runninghub_config(
                config_id=config_id,
                workflow_type="video",
                db=self._db,
                fallback=self._default_config,
            )
        except Exception as exc:  # pragma: no cover - fallback to default
            logger.warning("Falling back to default Runninghub video config: %s", exc)
            return self._default_config


__all__ = ["NcaVideoProvider", "FalVideoProvider", "RunningHubVideoProvider"]

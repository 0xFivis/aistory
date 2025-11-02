"""Image generation provider implementations."""
from __future__ import annotations

import time
import logging
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.services.comfyui_service import ComfyUIService
from app.services.liblib_service import LiblibService
from app.services.runninghub_config import (
    DEFAULT_IMAGE_WORKFLOW_CONFIG,
    RunningHubWorkflowConfig,
    get_runninghub_config,
)
from app.models.concurrency import ServiceConcurrencySlot
from app.services.concurrency_manager import concurrency_manager
from app.services.runninghub_service import RunningHubService
from .base import ImageGenerationProvider, MediaRequest, MediaResult


class LiblibImageProvider(ImageGenerationProvider):
    provider_name = "liblib"

    def __init__(self, db: Session) -> None:
        self._db = db
        self._current_lora: Optional[str] = None
        self._current_checkpoint: Optional[str] = None
        self._service = LiblibService(db)

    def apply_model_overrides(self, lora_id: Optional[str], checkpoint_id: Optional[str]) -> None:
        normalized_lora = lora_id or None
        normalized_checkpoint = checkpoint_id or None
        if (
            normalized_lora == self._current_lora
            and normalized_checkpoint == self._current_checkpoint
        ):
            return
        try:
            self._service.close()
        except Exception:  # pragma: no cover - defensive cleanup
            pass
        self._service = LiblibService(
            self._db,
            lora_id=normalized_lora,
            checkpoint_id=normalized_checkpoint,
        )
        self._current_lora = normalized_lora
        self._current_checkpoint = normalized_checkpoint

    def generate(self, request: MediaRequest) -> MediaResult:
        prompt = (request.prompt or "").strip()
        if not prompt:
            return MediaResult(status="failed", meta={"error": "prompt is empty"})

        response = self._service.generate_image(
            prompt=prompt,
            negative_prompt=request.negative_prompt,
            width=request.width or 1024,
            height=request.height or 1024,
            steps=(request.extra or {}).get("steps", 30),
            seed=(request.extra or {}).get("seed"),
        )

        meta = response if isinstance(response, dict) else {"raw": response}
        image_url: Optional[str] = None
        job_id: Optional[str] = None

        if isinstance(response, dict):
            image_url = response.get("image_url") or response.get("url")
            job_id = response.get("job_id") or response.get("task_id")
            if not image_url:
                data = response.get("data")
                if isinstance(data, list) and data:
                    first = data[0]
                    if isinstance(first, dict):
                        image_url = first.get("url") or first.get("image_url")
                        job_id = job_id or first.get("job_id")

        if image_url:
            return MediaResult(status="completed", resource_url=image_url, job_id=job_id, meta=meta)

        if job_id:
            return MediaResult(status="queued", job_id=job_id, meta=meta)

        # No useful output, treat as failure
        return MediaResult(status="failed", meta=meta)

    def __del__(self):  # pragma: no cover - defensive cleanup
        try:
            self._service.close()
        except Exception:
            pass


class ComfyUIImageProvider(ImageGenerationProvider):
    provider_name = "comfyui"

    def __init__(self, db: Optional[Session] = None) -> None:
        # ComfyUI service manages its own DB session lookup for credentials
        self._service = ComfyUIService()

    def generate(self, request: MediaRequest) -> MediaResult:
        prompt = (request.prompt or "").strip()
        if not prompt:
            return MediaResult(status="failed", meta={"error": "prompt is empty"})

        try:
            response = self._service.text_to_image(prompt=prompt)
        except Exception as exc:  # pragma: no cover - remote failure
            return MediaResult(status="failed", meta={"error": str(exc)})

        meta = response if isinstance(response, dict) else {"raw": response}
        image_url: Optional[str] = None
        job_id: Optional[str] = None

        if isinstance(response, dict):
            image_url = response.get("image_url") or response.get("url")
            job_id = response.get("job_id") or response.get("task_id")

            outputs = response.get("outputs")
            if not image_url and isinstance(outputs, list) and outputs:
                first = outputs[0]
                if isinstance(first, dict):
                    image_url = first.get("url") or first.get("image_url")
                    job_id = job_id or first.get("job_id") or first.get("task_id")

        if image_url:
            return MediaResult(status="completed", resource_url=image_url, job_id=job_id, meta=meta)

        if job_id:
            return MediaResult(status="queued", job_id=job_id, meta=meta)

        return MediaResult(status="failed", meta=meta)


logger = logging.getLogger(__name__)


class RunningHubImageProvider(ImageGenerationProvider):
    provider_name = "runninghub"

    WORKFLOW_ID = "1978319996189302785"
    INSTANCE_TYPE = "plus"
    DEFAULT_WIDTH = 864
    DEFAULT_HEIGHT = 1536
    DEFAULT_POLL_ATTEMPTS = 6
    DEFAULT_POLL_INTERVAL = 60.0
    DEFAULT_INITIAL_DELAY = 60.0
    DEFAULT_BUSY_WAIT = 10.0
    DEFAULT_CREATE_ATTEMPTS = 3

    def __init__(self, db: Session) -> None:
        self._db = db
        self._service = RunningHubService(db)
        self._default_config = get_runninghub_config(
            key="image.default",
            db=db,
            fallback=DEFAULT_IMAGE_WORKFLOW_CONFIG,
        )

    def _parse_int(self, value, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _parse_float(self, value, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def generate(self, request: MediaRequest) -> MediaResult:
        prompt = (request.prompt or "").strip()
        if not prompt:
            return MediaResult(status="failed", meta={"error": "prompt is empty"})

        raw_extra = request.extra
        extra: Dict[str, Any] = raw_extra if isinstance(raw_extra, dict) else {}
        config = self._resolve_config(extra)

        width = self._parse_int(
            request.width,
            config.resolve_default("width", self.DEFAULT_WIDTH),
        )
        height = self._parse_int(
            request.height,
            config.resolve_default("height", self.DEFAULT_HEIGHT),
        )

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

        node_info_list = extra.get("runninghub_node_info_list")
        if not node_info_list:
            context = {
                "prompt": prompt,
                "width": width,
                "height": height,
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
                "width": width,
                "height": height,
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
            feature="image",
            resource_id=self._build_resource_id(request),
            metadata={
                "scene_seq": (extra.get("scene_seq") if isinstance(extra, dict) else None),
                "task_id": extra.get("task_id") if isinstance(extra, dict) else None,
                "provider": "runninghub",
                "feature": "image",
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
                image_url = None
                if entries:
                    first = entries[0]
                    image_url = (
                        first.get("fileUrl")
                        or first.get("file_url")
                        or first.get("url")
                        or first.get("value")
                    )
                if image_url:
                    meta["entries"] = entries
                    release_status = ServiceConcurrencySlot.STATUS_RELEASED
                    release_meta = {"job_id": task_id, "status": "completed"}
                    return MediaResult(status="completed", resource_url=image_url, job_id=task_id, meta=meta)
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
            return f"task-{task_id}-scene-{scene_seq}-image"
        if task_id is not None:
            return f"task-{task_id}-image"
        if scene_seq is not None:
            return f"scene-{scene_seq}-image"
        return f"image-{int(time.time() * 1000)}"

    def _resolve_config(self, extra: Dict[str, Any]) -> RunningHubWorkflowConfig:
        config_id = extra.get("runninghub_image_workflow_config_id")
        if config_id is None:
            config_id = extra.get("runninghub_workflow_config_id")

        try:
            return get_runninghub_config(
                config_id=config_id,
                workflow_type="image",
                db=self._db,
                fallback=self._default_config,
            )
        except Exception as exc:  # pragma: no cover - fallback to default
            logger.warning("Falling back to default Runninghub image config: %s", exc)
            return self._default_config


__all__ = ["LiblibImageProvider", "ComfyUIImageProvider", "RunningHubImageProvider"]

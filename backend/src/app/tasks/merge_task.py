"""Celery 任务：素材合成（merge_video）"""
from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from celery import shared_task
from sqlalchemy.orm import Session

from app.celery_app import celery_app
from app.database import get_db_session
from app.models.media import Scene
from app.models.task import Task, TaskStep
from app.services.providers.base import ComposeInput, ComposeRequest
from app.services.providers.registry import resolve_task_provider
from app.services.providers.utils import collect_provider_candidates
from app.tasks.utils import ensure_provider_map
from app.services.storage_service import StorageService


_storage_service = StorageService()


def _build_compose_inputs(
    scenes: List[Scene],
    url_resolver: Callable[[Optional[str]], Optional[str]],
) -> Tuple[List[ComposeInput], List[Dict[str, Any]], List[Dict[str, Any]]]:
    compose_inputs: List[ComposeInput] = []
    concat_inputs: List[Dict[str, Any]] = []
    scene_refs: List[Dict[str, Any]] = []

    for scene in scenes:
        video_url = None
        video_source = None

        if scene.merge_status == 2 and scene.merge_video_url:
            video_url = scene.merge_video_url
            video_source = "merge"
        elif scene.video_status == 2 and scene.raw_video_url:
            video_url = scene.raw_video_url
            video_source = "raw"

        if not video_url:
            continue

        resolved_url = url_resolver(video_url)
        if not resolved_url:
            continue

        compose_inputs.append(
            ComposeInput(
                video_url=resolved_url,
                extra={
                    "scene_id": scene.id,
                    "scene_seq": scene.seq,
                    "video_source": video_source,
                },
            )
        )
        concat_inputs.append({"file_url": resolved_url})
        scene_refs.append(
            {
                "scene_id": scene.id,
                "scene_seq": scene.seq,
                "video_url": video_url,
                "resolved_video_url": resolved_url,
                "video_source": video_source,
            }
        )

    return compose_inputs, concat_inputs, scene_refs


def _build_concat_payload(clips: List[Dict[str, Any]]) -> Dict[str, Any]:
    filters: List[Dict[str, Any]] = []
    video_labels: List[str] = []
    audio_labels: List[str] = []

    for idx, clip in enumerate(clips):
        video_labels.append(f"[v{idx}]")
        audio_labels.append(f"[a{idx}]")
        filters.append({"filter": f"[{idx}:v]format=yuv420p,setpts=PTS-STARTPTS[v{idx}]"})
        filters.append({"filter": f"[{idx}:a]asetpts=PTS-STARTPTS[a{idx}]"})

    if video_labels:
        filters.append({"filter": f"{''.join(video_labels)}concat=n={len(clips)}:v=1:a=0[v]"})
    if audio_labels:
        filters.append({"filter": f"{''.join(audio_labels)}concat=n={len(clips)}:v=0:a=1[a]"})

    payload = {
        "id": f"concat-{int(time.time() * 1000)}",
        "inputs": clips,
        "filters": filters,
        "outputs": [
            {
                "options": [
                    {"option": "-map", "argument": "[v]"},
                    {"option": "-map", "argument": "[a]"},
                    {"option": "-c:v", "argument": "libx264"},
                    {"option": "-preset", "argument": "medium"},
                    {"option": "-crf", "argument": "23"},
                    {"option": "-c:a", "argument": "aac"},
                    {"option": "-pix_fmt", "argument": "yuv420p"},
                ]
            }
        ],
        "global_options": [{"option": "-y"}],
        "metadata": {
            "thumbnail": True,
            "filesize": True,
            "duration": True,
            "bitrate": True,
            "encoder": True,
        },
    }
    return payload


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def merge_video_task(self, task_id: int):
    db: Session = get_db_session()
    try:
        task = db.get(Task, task_id)
        if not task or task.is_deleted:
            return {"error": "任务不存在"}

        step = (
            db.query(TaskStep)
            .filter(TaskStep.task_id == task_id, TaskStep.step_name == "merge_video")
            .first()
        )
        if not step:
            return {"error": "合成步骤不存在"}

        step.status = 1
        step.error_msg = None
        db.commit()

        provider, provider_name = resolve_task_provider("media_compose", collect_provider_candidates(task), db)
        step.provider = provider_name
        db.commit()

        providers_map = ensure_provider_map(task.providers)
        providers_map["media_compose"] = provider_name
        task.providers = providers_map
        db.commit()

        scenes = (
            db.query(Scene)
            .filter(Scene.task_id == task_id)
            .order_by(Scene.seq.asc())
            .all()
        )

        def _resolve_url(value: Optional[str]) -> Optional[str]:
            if not value:
                return value
            if provider_name == "nca":
                return _storage_service.build_full_url(value)
            return value

        compose_inputs, concat_inputs, scene_refs = _build_compose_inputs(scenes, _resolve_url)
        if not concat_inputs:
            step.status = 3
            step.error_msg = "缺少可合成的视频片段"
            db.commit()
            return {"error": "缺少可合成的视频片段"}

        task_config = task.task_config or {}
        compose_config = {}
        if isinstance(task_config.get("compose"), dict):
            compose_config = task_config.get("compose") or {}

        compose_extra: Dict[str, Any] = {}
        if isinstance(compose_config.get("output"), dict):
            compose_extra["output"] = compose_config.get("output")
        if isinstance(compose_config.get("options"), dict):
            compose_extra["options"] = compose_config.get("options")
        if compose_config.get("timeout") is not None:
            compose_extra["timeout"] = compose_config.get("timeout")

        payload = _build_concat_payload(concat_inputs)

        compose_extra = compose_extra or {}
        compose_extra["compose_payload"] = payload

        compose_request = ComposeRequest(
            clips=compose_inputs,
            output_format=compose_config.get("format") or compose_config.get("output_format"),
            resolution=compose_config.get("resolution"),
            frame_rate=compose_config.get("frame_rate"),
            audio_bitrate=compose_config.get("audio_bitrate"),
            video_bitrate=compose_config.get("video_bitrate"),
            extra=compose_extra or None,
        )

        result = provider.compose(compose_request)

        job_id = result.job_id
        merged_video_url = result.video_url
        response_meta = result.meta if isinstance(result.meta, dict) else ({"raw": result.meta} if result.meta is not None else {})

        step.external_task_id = job_id

        candidate_values: List[Optional[str]] = [
            getattr(result, "video_api_path", None),
            merged_video_url,
            getattr(result, "video_relative_path", None),
            response_meta.get("video_api_path") if isinstance(response_meta, dict) else None,
            response_meta.get("video_relative_path") if isinstance(response_meta, dict) else None,
        ]

        merged_reference = None
        for candidate in candidate_values:
            if not candidate:
                continue
            merged_reference = _storage_service.resolve_reference(candidate)
            if merged_reference:
                break

        merged_video_api_path: Optional[str] = None
        if merged_reference:
            merged_video_api_path = merged_reference.api_path
        else:
            for candidate in candidate_values:
                if not candidate:
                    continue
                try:
                    merged_video_api_path = _storage_service.ensure_api_path(str(candidate))
                    break
                except ValueError:
                    continue

        if not merged_video_api_path and isinstance(merged_video_url, str):
            merged_video_api_path = merged_video_url

        if merged_video_api_path and isinstance(response_meta, dict):
            response_meta.setdefault("video_api_path", merged_video_api_path)

        step.result = {
            "provider": provider_name,
            "payload": payload,
            "job_id": job_id,
            "video_url": merged_video_api_path,
            "meta": response_meta,
            "scenes": scene_refs,
        }

        if merged_video_api_path:
            step.status = 2
            step.progress = 100

            task_result = task.result or {}
            task_result.update({
                "merge_provider": provider_name,
                "merged_video_url": merged_video_api_path,
                "merged_video_meta": response_meta,
                "merge_payload": payload,
            })
            task.result = task_result
            task.merged_video_url = merged_video_api_path
            task.status = 1
            task.progress = max(task.progress or 0, 90)
            db.commit()

            task_mode = getattr(task, "mode", None) or (task.task_config or {}).get("mode")
            if not task_mode:
                raise RuntimeError("任务未配置执行模式")
            if task_mode == "auto":
                try:
                    celery_app.send_task(
                        "app.tasks.finalize_task.finalize_video_task",
                        args=[task.id],
                        queue="default",
                        serializer="json",
                    )
                except Exception:
                    pass

            return {"video_url": merged_video_api_path}

        if job_id:
            step.status = 1
            step.progress = 50
            db.commit()
            return {"status": "queued", "job_id": job_id}

        step.status = 3
        step.error_msg = response_meta.get("error") if isinstance(response_meta, dict) else None
        if not step.error_msg:
            step.error_msg = "合成失败：缺少输出视频URL"
        step.progress = 0
        db.commit()
        return {"error": step.error_msg}

    except Exception as exc:
        db.rollback()
        step = (
            db.query(TaskStep)
            .filter(TaskStep.task_id == task_id, TaskStep.step_name == "merge_video")
            .first()
        )
        if step:
            step.status = 3
            step.error_msg = str(exc)
            db.commit()
        raise self.retry(exc=exc)
    finally:
        db.close()

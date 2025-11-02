"""Celery 任务：分镜音视频合成（scene_merge_task）"""
from __future__ import annotations

import math
import time
from typing import Any, Dict, Optional

from celery import shared_task
from sqlalchemy.orm import Session

from app.celery_app import celery_app
from app.database import get_db_session
from app.models.media import Scene
from app.models.task import Task, TaskStep
from app.services.nca_service import NCAService
from app.services.ffmpeg_service import FFmpegService
from app.services.storage_service import StorageService
from app.services.providers.utils import collect_provider_candidates
from app.tasks.utils import ensure_provider_map
from app.config.settings import get_settings

_storage_service = StorageService()


def _extract_first_value(payload: Any, keys: tuple[str, ...]) -> Optional[Any]:
    if isinstance(payload, dict):
        for key in keys:
            if key in payload and payload[key] is not None:
                return payload[key]
        for value in payload.values():
            found = _extract_first_value(value, keys)
            if found is not None:
                return found
    elif isinstance(payload, list):
        for item in payload:
            found = _extract_first_value(item, keys)
            if found is not None:
                return found
    return None


def _extract_duration(payload: Any) -> Optional[float]:
    value = _extract_first_value(payload, ("duration",))
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_media_url(payload: Any) -> Optional[str]:
    value = _extract_first_value(payload, ("video_url", "file_url", "url"))
    if value is None:
        return None
    return str(value)


def _compose_scene_with_audio_nca(
    service: NCAService,
    video_url: str,
    audio_url: str,
    frame_rate: int,
) -> Dict[str, Any]:
    video_metadata = service.get_media_metadata(video_url)
    audio_metadata = service.get_media_metadata(audio_url)

    video_duration = _extract_duration(video_metadata)
    audio_duration = _extract_duration(audio_metadata)

    if not video_duration or video_duration <= 0:
        raise RuntimeError("无法获取视频时长")
    if not audio_duration or audio_duration <= 0:
        raise RuntimeError("无法获取音频时长")

    required_frames = math.ceil(audio_duration * frame_rate)
    target_duration = required_frames / frame_rate
    ratio = target_duration / video_duration if video_duration else 1.0

    filter_string = (
        f"[0:v]setpts=PTS*{ratio:.8f},fps={frame_rate}[v_out];"
        f"[1:a]apad=whole_dur={target_duration:.8f},asetpts=PTS-STARTPTS[a_out]"
    )

    payload = {
        "id": f"scene-av-{int(time.time() * 1000)}",
        "inputs": [
            {"file_url": video_url},
            {"file_url": audio_url},
        ],
        "filters": [
            {"filter": filter_string},
        ],
        "outputs": [
            {
                "options": [
                    {"option": "-map", "argument": "[v_out]"},
                    {"option": "-map", "argument": "[a_out]"},
                    {"option": "-c:v", "argument": "libx264"},
                    {"option": "-preset", "argument": "fast"},
                    {"option": "-crf", "argument": "23"},
                    {"option": "-c:a", "argument": "aac"},
                    {"option": "-shortest"},
                ]
            }
        ],
        "metadata": {
            "duration": True,
            "filesize": True,
            "thumbnail": True,
        },
    }

    response = service.compose(payload)
    final_url_raw = _extract_media_url(response)
    final_url = service.resolve_media_url(final_url_raw)
    if not final_url:
        raise RuntimeError("NCA 合成未返回视频地址")

    job_id = _extract_first_value(response, ("job_id", "task_id"))

    return {
        "video_url": final_url,
        "video_url_raw": final_url_raw,
        "job_id": job_id,
        "filter": filter_string,
        "video_duration": video_duration,
        "audio_duration": audio_duration,
        "target_duration": target_duration,
        "speed_ratio": ratio,
        "compose_payload": payload,
        "compose_response": response,
        "video_metadata": video_metadata,
        "audio_metadata": audio_metadata,
        "provider": "nca",
    }


def _compose_scene_with_audio_ffmpeg(
    service: FFmpegService,
    *,
    video_url: str,
    audio_url: str,
    frame_rate: int,
    task_id: int,
    scene_id: int,
    scene_seq: int,
) -> Dict[str, Any]:
    result = service.compose_scene_with_audio(
        video_url=video_url,
        audio_url=audio_url,
        frame_rate=frame_rate,
        task_id=task_id,
        scene_id=scene_id,
        scene_seq=scene_seq,
    )
    result["provider"] = "ffmpeg"
    return result


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def merge_scene_media_task(self, task_id: int, scene_id: Optional[int] = None):
    """对已生成的分镜视频与音频进行逐镜头合成"""
    db: Session = get_db_session()
    try:
        task = db.get(Task, task_id)
        if not task or task.is_deleted:
            return {"error": "任务不存在"}

        step = (
            db.query(TaskStep)
            .filter(TaskStep.task_id == task_id, TaskStep.step_name == "merge_scene_media")
            .first()
        )
        if not step:
            return {"error": "音视频合成步骤不存在"}

        step.status = 1
        db.commit()

        task_config = task.task_config or {}
        if not isinstance(task_config, dict):
            task_config = {}
        video_config: Dict[str, Any] = {}
        if isinstance(task_config.get("video"), dict):
            video_config = task_config.get("video") or {}

        frame_rate_value = video_config.get("frame_rate")
        if frame_rate_value is None:
            frame_rate_value = task_config.get("frame_rate") if isinstance(task_config.get("frame_rate"), (int, float)) else None
        if frame_rate_value is None:
            frame_rate_value = 25
        try:
            frame_rate_default = int(frame_rate_value)
        except (TypeError, ValueError) as exc:
            raise RuntimeError("scene_merge 帧率配置无效") from exc
        if frame_rate_default <= 0:
            raise RuntimeError("scene_merge 帧率配置无效")

        scenes = (
            db.query(Scene)
            .filter(Scene.task_id == task_id)
            .order_by(Scene.seq.asc())
            .all()
        )

        target_scenes = scenes
        if scene_id is not None:
            target_scenes = [sc for sc in scenes if sc.id == scene_id]
            if not target_scenes:
                return {"error": f"scene {scene_id} not found"}

        settings = get_settings()
        provider_candidates = collect_provider_candidates(task)
        default_provider = settings.provider_defaults.get("scene_merge") if settings else None
        provider_name = provider_candidates.get("scene_merge") or default_provider
        if not provider_name:
            raise RuntimeError("未配置 scene_merge provider")
        provider_name = str(provider_name).strip().lower()
        if provider_name not in {"nca", "ffmpeg"}:
            raise RuntimeError("不支持的 scene_merge provider")

        step.provider = provider_name
        db.commit()

        providers_map = ensure_provider_map(task.providers)
        providers_map["scene_merge"] = provider_name
        task.providers = providers_map
        db.commit()

        if provider_name == "ffmpeg":
            compose_service: Any = FFmpegService()
        else:
            compose_service = NCAService(db)

        for scene in target_scenes:
            if scene.merge_status == 2 and scene.merge_video_url:
                continue
            if scene.video_status != 2 or not scene.raw_video_url:
                continue
            if scene.audio_status != 2 or not scene.audio_url:
                continue

            scene.merge_status = 1
            scene.error_msg = None
            db.commit()

            try:
                input_video_url = scene.raw_video_url
                input_audio_url = scene.audio_url
                if provider_name == "nca":
                    input_video_url = _storage_service.build_full_url(input_video_url)
                    input_audio_url = _storage_service.build_full_url(input_audio_url)
                if provider_name == "ffmpeg":
                    compose_meta = _compose_scene_with_audio_ffmpeg(
                        compose_service,
                        video_url=input_video_url or scene.raw_video_url,
                        audio_url=input_audio_url or scene.audio_url,
                        frame_rate=frame_rate_default,
                        task_id=task_id,
                        scene_id=scene.id,
                        scene_seq=scene.seq,
                    )
                else:
                    compose_meta = _compose_scene_with_audio_nca(
                        compose_service,
                        video_url=input_video_url or scene.raw_video_url,
                        audio_url=input_audio_url or scene.audio_url,
                        frame_rate=frame_rate_default,
                    )
            except Exception as exc:
                existing_meta = scene.merge_meta if isinstance(scene.merge_meta, dict) else {}
                updated_meta = dict(existing_meta)
                updated_meta["compose_av_error"] = str(exc)
                updated_meta["provider"] = provider_name

                scene.merge_status = 3
                scene.merge_retry_count = (scene.merge_retry_count or 0) + 1
                scene.merge_meta = updated_meta
                scene.error_msg = str(exc)
                db.commit()
                continue

            scene.merge_status = 2
            scene.merge_retry_count = 0
            stored_video_candidate = (
                compose_meta.get("video_api_path")
                or compose_meta.get("video_relative_path")
                or compose_meta.get("video_url")
            )
            stored_reference = _storage_service.resolve_reference(stored_video_candidate) if stored_video_candidate else None
            if stored_reference:
                stored_video_url = stored_reference.api_path
            elif stored_video_candidate:
                try:
                    stored_video_url = _storage_service.ensure_api_path(str(stored_video_candidate))
                except ValueError:
                    stored_video_url = str(stored_video_candidate)
            else:
                stored_video_url = None

            scene.merge_video_url = stored_video_url
            scene.merge_video_provider = provider_name
            scene.merge_job_id = compose_meta.get("job_id")
            scene.merge_meta = compose_meta
            scene.error_msg = None

            video_meta = scene.video_meta if isinstance(scene.video_meta, dict) else {}
            if stored_video_url:
                merged_video_meta = dict(video_meta)
                merged_video_meta["final_video_url"] = stored_video_url
                scene.video_meta = merged_video_meta

            db.commit()

        overall_completed = sum(1 for sc in scenes if sc.merge_status == 2)
        overall_failed = sum(1 for sc in scenes if sc.merge_status == 3)
        overall_processing = sum(1 for sc in scenes if sc.merge_status == 1)
        total_targets = sum(
            1
            for sc in scenes
            if sc.video_status == 2 and sc.raw_video_url and sc.audio_status == 2 and sc.audio_url
        )

        step.result = {
            "provider": provider_name,
            "completed": overall_completed,
            "failed": overall_failed,
            "processing": overall_processing,
            "frame_rate": frame_rate_default,
        }
        step.error_msg = None

        if total_targets:
            step.progress = int(overall_completed / total_targets * 100)
        else:
            step.progress = 100

        if overall_failed == total_targets and total_targets > 0:
            step.status = 3
            step.error_msg = "音视频合成全部失败"
            step.progress = 0
        elif overall_failed > 0 and overall_completed > 0:
            step.status = 6
            step.error_msg = "部分音视频合成失败"
        elif overall_processing > 0 or (total_targets > overall_completed + overall_failed):
            step.status = 1
        else:
            step.status = 2

        db.commit()

        task_mode = getattr(task, "mode", None) or (task.task_config or {}).get("mode", "auto")
        # Only auto-continue when the step is fully completed (status == 2). Do NOT continue on INTERRUPTED (6).
        if scene_id is None and task_mode == "auto" and step.status == 2:
            try:
                celery_app.send_task(
                    "app.tasks.merge_task.merge_video_task",
                    args=[task.id],
                    queue="default",
                    serializer="json",
                )
            except Exception:
                pass

        return {"merged": overall_completed, "provider": provider_name}
    except Exception as exc:
        db.rollback()
        step = (
            db.query(TaskStep)
            .filter(TaskStep.task_id == task_id, TaskStep.step_name == "merge_scene_media")
            .first()
        )
        if step:
            step.status = 3
            step.error_msg = str(exc)
            db.commit()
        raise self.retry(exc=exc)
    finally:
        db.close()

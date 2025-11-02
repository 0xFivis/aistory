"""Celery 任务：音频生成（audio_task）"""
from typing import Optional

import logging

from celery import shared_task
from celery.exceptions import Retry
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.celery_app import celery_app
from app.database import get_db_session
from app.models.media import Scene
from app.models.task import Task, TaskStep
from app.services.providers.base import MediaRequest
from app.services.providers.registry import resolve_task_provider
from app.services.providers.utils import collect_provider_candidates
from app.services.storage_service import StorageService
from app.tasks.utils import ensure_provider_map
from app.tasks.utils.interrupts import StepInterruptController, summarize_status_counts
from app.services.audio_postprocess import get_audio_post_processor
from app.services.ffmpeg_service import FFmpegService
from app.utils.timezone import naive_now


_storage_service = StorageService()

logger = logging.getLogger(__name__)

_audio_post_processor = get_audio_post_processor()
_ffmpeg_service = FFmpegService()


AUDIO_LOCK_NAME = "audio_generation_lock"


def acquire_audio_lock(db: Session) -> bool:
    result = db.execute(text("SELECT GET_LOCK(:name, 0)"), {"name": AUDIO_LOCK_NAME})
    value = result.scalar()
    return bool(value)


def _probe_audio_duration(audio_url: Optional[str]) -> Optional[float]:
    if not audio_url:
        return None
    try:
        metadata = _ffmpeg_service.get_media_metadata(audio_url)
    except Exception:
        logger.exception("Failed to probe audio duration for %s", audio_url)
        return None
    duration = metadata.get("duration") if isinstance(metadata, dict) else None
    try:
        return float(duration) if duration is not None else None
    except (TypeError, ValueError):
        return None


def release_audio_lock(db: Session) -> None:
    db.execute(text("SELECT RELEASE_LOCK(:name)"), {"name": AUDIO_LOCK_NAME})

@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def generate_audio_task(self, task_id: int, scene_id: Optional[int] = None):
    """异步音频生成任务"""
    db: Session = get_db_session()
    lock_acquired = False
    try:
        task = db.get(Task, task_id)
        if not task or task.is_deleted:
            return {"error": "任务不存在"}
        step = db.query(TaskStep).filter(TaskStep.task_id == task_id, TaskStep.step_name == "generate_audio").first()
        if not step:
            return {"error": "音频生成步骤不存在"}

        provider, provider_name = resolve_task_provider("audio", collect_provider_candidates(task), db)
        step.provider = provider_name
        db.commit()

        providers_map = ensure_provider_map(task.providers)
        providers_map["audio"] = provider_name
        task.providers = providers_map
        db.commit()

        requires_lock = str(provider_name).lower() == "fishaudio"
        if requires_lock:
            lock_acquired = acquire_audio_lock(db)
            if not lock_acquired:
                raise self.retry(exc=RuntimeError("Fish Audio 服务已有任务执行中"), countdown=10)

        step.status = 1
        db.commit()

        task_config = task.task_config or {}
        if not isinstance(task_config, dict):
            task_config = {}
        def _coerce_bool(value, default):
            if value is None:
                return default
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.strip().lower() in {"1", "true", "yes", "on", "y"}
            return bool(value)

        audio_config = {}
        if isinstance(task_config.get("audio"), dict):
            audio_config = task_config.get("audio") or {}

        task_trim_enabled = _coerce_bool(task_config.get("audio_trim_silence"), True)
        audio_trim_default = _coerce_bool(audio_config.get("trim_silence"), task_trim_enabled)

        scenes = (
            db.query(Scene)
            .filter(Scene.task_id == task_id)
            .order_by(Scene.seq)
            .all()
        )

        target_scenes = scenes
        if scene_id is not None:
            target_scenes = [sc for sc in scenes if sc.id == scene_id]
            if not target_scenes:
                return {"error": f"scene {scene_id} not found"}

        interrupt_helper = StepInterruptController(
            db=db,
            step=step,
            status_attr="audio_status",
            job_id_attr="audio_job_id",
            url_attr="audio_url",
            extra_reset=lambda sc: setattr(sc, "audio_meta", None),
        )

        reset_count = interrupt_helper.reset_interrupted(target_scenes)
        if reset_count:
            logger.info("Reset %s interrupted audio scenes to pending before rerun", reset_count)

        step = interrupt_helper.step
        target_scene_ids = [sc.id for sc in target_scenes]

        completed_count = 0
        queued_count = 0
        failed_count = 0

        for scene_pk in target_scene_ids:
            if interrupt_helper.should_abort():
                step = interrupt_helper.step
                logger.info("Audio step interrupted, aborting remaining scenes")
                break

            step = interrupt_helper.step
            scene = db.get(Scene, scene_pk)
            if not scene:
                continue

            if scene.audio_status == 2:
                continue

            scene_params = scene.params if isinstance(scene.params, dict) else {}
            scene_trim_enabled = _coerce_bool(scene_params.get("trim_silence"), audio_trim_default)

            voice_id = (
                scene_params.get("voice_id")
                or audio_config.get("voice_id")
                or task_config.get("audio_voice_value")
                or getattr(task, "selected_voice_id", None)
                or task_config.get("audio_voice_id")
            )
            if not voice_id:
                raise RuntimeError("缺少音色配置，无法生成音频")

            if scene.audio_status != 1:
                scene.audio_status = 1
            scene.audio_duration = None
            scene.error_msg = None
            scene.started_at = naive_now()
            try:
                db.commit()
            except Exception as mark_exc:
                logger.exception(
                    "Failed to mark audio scene %s as processing: %s",
                    getattr(scene, "id", None),
                    mark_exc,
                )
                try:
                    db.rollback()
                except Exception:
                    pass

            try:
                result = provider.generate(
                    MediaRequest(
                        text=scene.narration_text,
                        voice_id=voice_id,
                        extra={
                            "task_id": task.id,
                            "scene_seq": scene.seq,
                            "format": audio_config.get("format") or task_config.get("audio_format"),
                            "sample_rate": audio_config.get("sample_rate") or task_config.get("audio_sample_rate"),
                            "voice_id": voice_id,
                        },
                    )
                )
            except Exception as exc:  # pragma: no cover - remote failure
                scene.audio_status = 3
                scene.audio_provider = provider_name
                scene.audio_retry_count = (scene.audio_retry_count or 0) + 1
                scene.error_msg = str(exc)
                scene.finished_at = naive_now()
                scene.audio_duration = None
                failed_count += 1
                db.commit()
                continue

            scene.audio_provider = provider_name
            scene.audio_job_id = getattr(result, "job_id", None)
            scene.audio_meta = result.meta

            if interrupt_helper.handle_interrupt_after_provider(scene):
                db.commit()
                step = interrupt_helper.step
                logger.info("Scene %s marked interrupted after provider response", scene_pk)
                break

            step = interrupt_helper.step

            if result.status == "completed" and result.resource_url:
                storage_url = None
                reference = None
                if isinstance(result.meta, dict):
                    candidate_path = result.meta.get("api_path") or result.meta.get("relative_path")
                    if candidate_path:
                        try:
                            reference = _storage_service.resolve_reference(candidate_path)
                        except Exception:  # pragma: no cover - defensive
                            reference = None
                if not reference and result.resource_url:
                    reference = _storage_service.resolve_reference(result.resource_url)
                if reference:
                    storage_url = reference.api_path
                else:
                    try:
                        storage_url = _storage_service.ensure_api_path(result.resource_url)
                    except Exception:
                        storage_url = result.resource_url
                scene.audio_url = storage_url
                scene.audio_status = 2
                scene.error_msg = None
                scene.finished_at = naive_now()
                completed_count += 1

                duration_value: Optional[float] = None
                if scene_trim_enabled and storage_url:
                    try:
                        trim_result = _audio_post_processor.process(
                            storage_url,
                            threshold_db=-35.0,
                            max_leading=0.1,
                            max_trailing=0.1,
                        )
                        if trim_result.report:
                            existing_meta = scene.audio_meta if isinstance(scene.audio_meta, dict) else {}
                            meta = dict(existing_meta)
                            report_block = dict(meta.get("silence_report") or {})
                            remaining_leading = max(
                                trim_result.report.leading_silence - trim_result.removed_leading,
                                0.0,
                            )
                            remaining_trailing = max(
                                trim_result.report.trailing_silence - trim_result.removed_trailing,
                                0.0,
                            )
                            report_block.update(
                                {
                                    "tool": trim_result.tool,
                                    "leading": trim_result.report.leading_silence,
                                    "trailing": trim_result.report.trailing_silence,
                                    "duration": trim_result.report.duration,
                                    "remaining_leading": remaining_leading,
                                    "remaining_trailing": remaining_trailing,
                                }
                            )
                            meta["silence_report"] = report_block
                            scene.audio_meta = meta
                            try:
                                duration_value = float(trim_result.report.duration)
                            except (TypeError, ValueError):
                                duration_value = None
                        if trim_result.trimmed and trim_result.reference:
                            original_url = scene.audio_url
                            scene.audio_url = trim_result.reference.api_path
                            existing_meta = scene.audio_meta if isinstance(scene.audio_meta, dict) else {}
                            meta = dict(existing_meta)
                            trim_block = dict(meta.get("silence_trim") or {})
                            trim_block.update(
                                {
                                    "tool": trim_result.tool,
                                    "leading_removed": trim_result.removed_leading,
                                    "trailing_removed": trim_result.removed_trailing,
                                    "remaining_leading": max(
                                        trim_result.report.leading_silence - trim_result.removed_leading,
                                        0.0,
                                    ),
                                    "remaining_trailing": max(
                                        trim_result.report.trailing_silence - trim_result.removed_trailing,
                                        0.0,
                                    ),
                                    "original_url": original_url,
                                    "new_url": trim_result.reference.api_path,
                                }
                            )
                            meta["silence_trim"] = trim_block
                            scene.audio_meta = meta
                            try:
                                db.commit()
                            except Exception:
                                db.rollback()
                                raise
                    except Exception:
                        logger.exception(
                            "Failed to trim silence for audio scene %s",
                            getattr(scene, "id", None),
                        )
                if duration_value is None:
                    duration_value = _probe_audio_duration(scene.audio_url)
                scene.audio_duration = duration_value
            elif result.status == "queued":
                scene.audio_status = 1
                scene.error_msg = None
                scene.audio_duration = None
                queued_count += 1
            else:
                scene.audio_status = 3
                scene.error_msg = (result.meta or {}).get("error") if isinstance(result.meta, dict) else None
                scene.audio_retry_count = (scene.audio_retry_count or 0) + 1
                scene.finished_at = naive_now()
                scene.audio_duration = None
                failed_count += 1

            db.commit()

        scenes = (
            db.query(Scene)
            .filter(Scene.task_id == task_id)
            .order_by(Scene.seq)
            .all()
        )

        overall_completed, overall_queued, overall_failed, pending_count = summarize_status_counts(
            scenes,
            status_attr="audio_status",
        )

        step = interrupt_helper.step
        step.result = {
            "provider": provider_name,
            "completed": overall_completed,
            "queued": overall_queued,
            "failed": overall_failed,
        }

        total_scenes = len(scenes)
        if total_scenes:
            step.progress = int(overall_completed / total_scenes * 100)
        else:
            step.progress = 100

        if step.status != 6:
            step.error_msg = None
            if overall_failed == total_scenes and total_scenes > 0:
                step.status = 3
                step.error_msg = "音频生成全部失败"
                step.progress = 0
            elif overall_failed > 0 and overall_completed > 0:
                step.status = 6
                step.error_msg = "部分音频生成失败"
            elif overall_queued > 0 or pending_count > 0:
                step.status = 1
            else:
                step.status = 2

        db.commit()

        task_mode = getattr(task, 'mode', None) or (task.task_config or {}).get('mode')
        if not task_mode:
            raise RuntimeError("任务未配置执行模式")
        # Only auto-continue when the step is fully completed (status == 2). Do NOT continue on INTERRUPTED (6).
        if scene_id is None and task_mode == 'auto' and step.status == 2:
            celery_app.send_task(
                'app.tasks.video_task.generate_video_task',
                args=[task.id],
                queue='default',
                serializer='json',
            )

        return {"audio": len(target_scenes)}
    except Retry:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        step = db.query(TaskStep).filter(TaskStep.task_id == task_id, TaskStep.step_name == "generate_audio").first()
        if step:
            step.status = 3
            step.error_msg = str(e)
            db.commit()
        raise self.retry(exc=e)
    finally:
        if lock_acquired:
            try:
                release_audio_lock(db)
            except Exception:
                pass
        db.close()

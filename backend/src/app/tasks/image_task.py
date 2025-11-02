"""Celery 任务：图片生成（image_task）"""
from typing import Optional
from uuid import uuid4
from sqlalchemy import update as sa_update

from celery import shared_task
from sqlalchemy.orm import Session

from app.celery_app import celery_app
from app.database import get_db_session
from app.models.media import Scene
from app.models.task import Task, TaskStep
from app.services.providers.base import MediaRequest
from app.services.providers.registry import resolve_task_provider
from app.services.providers.utils import collect_provider_candidates
from app.tasks.utils import ensure_provider_map
from app.tasks.utils.interrupts import StepInterruptController, summarize_status_counts
from app.services.style_preset_service import merge_style_preset
from app.utils.timezone import naive_now
import logging
from datetime import timedelta
import traceback

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def generate_images_task(self, task_id: int, scene_id: Optional[int] = None):
    """异步图片生成任务"""
    db: Session = get_db_session()
    try:
        task = db.get(Task, task_id)
        if not task or task.is_deleted:
            return {"error": "任务不存在"}

        step = (
            db.query(TaskStep)
            .filter(TaskStep.task_id == task_id, TaskStep.step_name == "generate_images")
            .first()
        )
        if not step:
            return {"error": "图片生成步骤不存在"}

        step.status = 1
        db.commit()

        task_config = task.task_config or {}
        if not isinstance(task_config, dict):
            task_config = {}

        merged_config, storyboard_config, preset = merge_style_preset(db, task_config)
        if task_config != merged_config:
            task.task_config = merged_config
            db.commit()
        task_config = merged_config

        provider, provider_name = resolve_task_provider("image", collect_provider_candidates(task), db)
        lora_id = task_config.get("lora_id") or task_config.get("liblib_lora_id")
        checkpoint_id = (
            task_config.get("checkpoint_id")
            or task_config.get("model_id")
            or task_config.get("liblib_model_id")
        )
        if hasattr(provider, "apply_model_overrides"):
            provider.apply_model_overrides(lora_id, checkpoint_id)
        step.provider = provider_name
        db.commit()

        providers_map = ensure_provider_map(task.providers)
        providers_map["image"] = provider_name
        task.providers = providers_map
        db.commit()

        style_meta = task_config.get("style_meta") if isinstance(task_config.get("style_meta"), dict) else {}
        runninghub_meta = style_meta.get("runninghub") if isinstance(style_meta.get("runninghub"), dict) else {}
        runninghub_image_workflow_id = runninghub_meta.get("image_workflow_config_id")

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
            status_attr="image_status",
            celery_id_attr="image_celery_id",
            job_id_attr="image_job_id",
            url_attr="image_url",
            extra_reset=lambda sc: setattr(sc, "image_meta", None),
            interrupt_clear_attrs=("image_celery_id",),
        )

        reset_count = interrupt_helper.reset_interrupted(target_scenes)
        if reset_count:
            logger.info("Reset %s interrupted image scenes to pending before rerun", reset_count)

        step = interrupt_helper.step
        target_scene_ids = [sc.id for sc in target_scenes]

        completed_count = 0
        queued_count = 0
        failed_count = 0
        LOCK_WINDOW = timedelta(seconds=30)

        for scene_pk in target_scene_ids:
            if interrupt_helper.should_abort():
                step = interrupt_helper.step
                logger.info("Image step interrupted, aborting remaining scenes")
                break

            step = interrupt_helper.step

            scene = db.get(Scene, scene_pk)
            if not scene:
                continue

            try:
                logger.debug(
                    "Processing scene id=%s seq=%s status=%s existing_celery=%s",
                    getattr(scene, "id", None),
                    getattr(scene, "seq", None),
                    getattr(scene, "image_status", None),
                    getattr(scene, "image_celery_id", None),
                )

                if scene.image_status == 2:
                    logger.debug("Skipping scene %s because already completed", getattr(scene, "id", None))
                    continue

                if scene.image_status == 1 and scene.started_at:
                    age = naive_now() - scene.started_at
                    if age < LOCK_WINDOW:
                        logger.debug(
                            "Skipping scene %s because started %s seconds ago (< lock_window)",
                            getattr(scene, "id", None),
                            age.total_seconds(),
                        )
                        continue

                try:
                    existing_celery_id = getattr(scene, "image_celery_id", None)
                except Exception as ex_get:
                    existing_celery_id = None
                    logger.exception(
                        "Failed to read image_celery_id for scene %s: %s",
                        getattr(scene, "id", None),
                        ex_get,
                    )
                if existing_celery_id and str(existing_celery_id).strip():
                    logger.debug(
                        "Skipping scene %s because image_celery_id is present: %s",
                        getattr(scene, "id", None),
                        existing_celery_id,
                    )
                    continue

                scene.image_status = 1
                scene.error_msg = None
                scene.started_at = naive_now()

                current_request_id = None
                try:
                    current_request_id = str(self.request.id)
                except Exception as ex_req:
                    logger.exception(
                        "Unable to read self.request.id in worker for scene %s: %s",
                        getattr(scene, "id", None),
                        ex_req,
                    )

                if current_request_id:
                    try:
                        scene.image_celery_id = current_request_id
                        db.commit()
                        logger.debug(
                            "Wrote image_celery_id=%s for scene %s",
                            current_request_id,
                            getattr(scene, "id", None),
                        )
                    except Exception as ex_write:
                        try:
                            db.rollback()
                        except Exception:
                            pass
                        logger.exception(
                            "Failed to commit image_celery_id for scene %s: %s",
                            getattr(scene, "id", None),
                            ex_write,
                        )
                        try:
                            db.execute(
                                sa_update(Scene)
                                .where(Scene.id == scene.id)
                                .values(
                                    image_celery_id=current_request_id,
                                    image_status=1,
                                    started_at=scene.started_at,
                                )
                            )
                            db.commit()
                            logger.debug(
                                "Fallback UPDATE wrote image_celery_id=%s for scene %s",
                                current_request_id,
                                getattr(scene, "id", None),
                            )
                        except Exception as ex_update:
                            try:
                                db.rollback()
                            except Exception:
                                pass
                            logger.exception(
                                "Fallback update also failed for scene %s: %s",
                                getattr(scene, "id", None),
                                ex_update,
                            )
                            scene.image_celery_id = None
                else:
                    try:
                        db.commit()
                    except Exception as ex_commit:
                        logger.exception(
                            "Failed to commit scene state (without image_celery_id) for scene %s: %s",
                            getattr(scene, "id", None),
                            ex_commit,
                        )

                try:
                    result = provider.generate(
                        MediaRequest(
                            prompt=scene.image_prompt,
                            width=(scene.image_meta or {}).get("width") if scene.image_meta else None,
                            height=(scene.image_meta or {}).get("height") if scene.image_meta else None,
                            extra={
                                "task_id": task.id,
                                "scene_seq": scene.seq,
                                **(
                                    {"runninghub_image_workflow_config_id": runninghub_image_workflow_id}
                                    if provider_name == "runninghub" and runninghub_image_workflow_id
                                    else {}
                                ),
                            },
                        )
                    )
                except Exception as exc:  # pragma: no cover - remote failure
                    logger.exception("Provider.generate failed for scene %s: %s", getattr(scene, "id", None), exc)
                    scene.image_status = 3
                    scene.image_provider = provider_name
                    scene.image_retry_count = (scene.image_retry_count or 0) + 1
                    scene.error_msg = str(exc)
                    scene.finished_at = naive_now()
                    failed_count += 1
                    try:
                        _clear_id = getattr(scene, "image_celery_id", None)
                        if _clear_id:
                            scene.image_celery_id = None
                        db.commit()
                        logger.debug(
                            "Cleared image_celery_id after failure for scene %s (was=%s)",
                            getattr(scene, "id", None),
                            _clear_id,
                        )
                    except Exception as ex_clear:
                        try:
                            db.rollback()
                        except Exception:
                            pass
                        logger.exception(
                            "Failed to clear image_celery_id after provider error for scene %s: %s",
                            getattr(scene, "id", None),
                            ex_clear,
                        )
                    continue

                scene.image_provider = provider_name
                scene.image_job_id = getattr(result, "job_id", None) or (result.meta or {}).get("job_id")
                scene.image_meta = result.meta

                if interrupt_helper.handle_interrupt_after_provider(scene):
                    db.commit()
                    step = interrupt_helper.step
                    logger.info("Scene %s marked interrupted after provider response", scene_pk)
                    break

                step = interrupt_helper.step

                old_celery_id = getattr(scene, "image_celery_id", None)
                try:
                    if result.status == "completed" and result.resource_url:
                        scene.image_url = result.resource_url
                        scene.image_status = 2
                        scene.error_msg = None
                        scene.finished_at = naive_now()
                        try:
                            current_stored = getattr(scene, "image_celery_id", None)
                            if current_stored and str(current_stored) == str(current_request_id):
                                scene.image_celery_id = None
                                logger.debug(
                                    "Cleared image_celery_id for scene %s after completion (was=%s)",
                                    getattr(scene, "id", None),
                                    current_stored,
                                )
                            else:
                                scene.image_celery_id = None
                                logger.warning(
                                    "image_celery_id mismatch/cleanup for scene %s: stored=%s expected=%s",
                                    getattr(scene, "id", None),
                                    current_stored,
                                    current_request_id,
                                )
                        except Exception as ex_clear2:
                            logger.exception(
                                "Error while attempting to clear image_celery_id for scene %s: %s",
                                getattr(scene, "id", None),
                                ex_clear2,
                            )
                        completed_count += 1
                    elif result.status == "queued":
                        scene.image_status = 1
                        scene.error_msg = None
                        queued_count += 1
                    else:
                        scene.image_status = 3
                        scene.error_msg = (result.meta or {}).get("error") if result.meta else None
                        scene.image_retry_count = (scene.image_retry_count or 0) + 1
                        scene.finished_at = naive_now()
                        try:
                            current_stored = getattr(scene, "image_celery_id", None)
                            if current_stored and str(current_stored) == str(current_request_id):
                                scene.image_celery_id = None
                                logger.debug(
                                    "Cleared image_celery_id for scene %s after failure branch (was=%s)",
                                    getattr(scene, "id", None),
                                    current_stored,
                                )
                            else:
                                scene.image_celery_id = None
                                logger.warning(
                                    "image_celery_id mismatch/cleanup for scene %s in failure branch: stored=%s expected=%s",
                                    getattr(scene, "id", None),
                                    current_stored,
                                    current_request_id,
                                )
                        except Exception as ex_clear3:
                            logger.exception(
                                "Error while attempting to clear image_celery_id in failure branch for scene %s: %s",
                                getattr(scene, "id", None),
                                ex_clear3,
                            )
                        failed_count += 1

                    db.commit()
                except Exception as ex_commit_all:
                    try:
                        db.rollback()
                    except Exception:
                        pass
                    logger.exception(
                        "Failed to commit scene updates for scene %s (completed=%s queued=%s failed=%s): %s",
                        getattr(scene, "id", None),
                        completed_count,
                        queued_count,
                        failed_count,
                        ex_commit_all,
                    )
                    continue

            except Exception as scene_exc:
                logger.exception(
                    "Unhandled exception while processing scene %s: %s\n%s",
                    getattr(scene, "id", None),
                    scene_exc,
                    traceback.format_exc(),
                )
                try:
                    scene.image_status = 3
                    scene.error_msg = str(scene_exc)
                    scene.finished_at = naive_now()
                    try:
                        scene.image_celery_id = None
                    except Exception:
                        pass
                    db.commit()
                except Exception:
                    try:
                        db.rollback()
                    except Exception:
                        pass
                failed_count += 1
                continue

        scenes = (
            db.query(Scene)
            .filter(Scene.task_id == task_id)
            .order_by(Scene.seq)
            .all()
        )

        overall_completed, overall_queued, overall_failed, pending_count = summarize_status_counts(
            scenes,
            status_attr="image_status",
        )

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
                step.error_msg = "图片生成全部失败"
                step.progress = 0
            elif overall_failed > 0 and overall_completed > 0:
                step.status = 6
                step.error_msg = "部分图片生成失败"
            elif overall_queued > 0 or pending_count > 0:
                step.status = 1
            else:
                step.status = 2

        db.commit()

        task_mode = getattr(task, "mode", None) or (task.task_config or {}).get("mode")
        if not task_mode:
            raise RuntimeError("任务未配置执行模式")

        if scene_id is None and task_mode == "auto" and step.status == 2:
            try:
                celery_app.send_task(
                    "app.tasks.audio_task.generate_audio_task",
                    args=[task.id],
                    queue="default",
                    serializer="json",
                )
            except Exception:
                logger.exception("Failed to enqueue audio task for task %s", getattr(task, "id", None))

        return {"images": len(target_scene_ids)}

    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        step = (
            db.query(TaskStep)
            .filter(TaskStep.task_id == task_id, TaskStep.step_name == "generate_images")
            .first()
        )
        if step:
            step.status = 3
            step.error_msg = str(e)
            try:
                db.commit()
            except Exception:
                pass
        raise self.retry(exc=e)
    finally:
        db.close()


@shared_task(bind=True)
def poll_image_job_status(self, scene_id: Optional[int] = None, task_id: Optional[int] = None, max_attempts: int = 6, interval_seconds: int = 30):
    """Poll provider job status for a single scene or all scenes in a task that have a job id.

    - If scene_id provided, only poll that scene.
    - If task_id provided, poll all scenes under that task which have image_job_id and are not completed.
    """
    from app.services.runninghub_service import RunningHubService
    from app.services.liblib_service import LiblibService
    from app.services.comfyui_service import ComfyUIService

    db: Session = get_db_session()
    try:
        candidates = []
        if scene_id:
            sc = db.get(Scene, scene_id)
            if sc:
                candidates = [sc]
        elif task_id:
            candidates = db.query(Scene).filter(Scene.task_id == task_id, Scene.image_job_id != None, Scene.image_status != 2).all()
        else:
            return {"polled": 0}

        polled = 0
        for sc in candidates:
            provider_name = (sc.image_provider or "").lower()
            job_id = sc.image_job_id
            if not job_id:
                continue

            # pick service by provider
            service = None
            try:
                if provider_name == "runninghub":
                    service = RunningHubService(db)
                    status, payload = service.wait_for_task(job_id, max_attempts=max_attempts, interval_seconds=interval_seconds)
                    if status == "success":
                        entries = service.extract_file_entries(payload)
                        image_url = None
                        if entries:
                            first = entries[0]
                            image_url = first.get("fileUrl") or first.get("file_url") or first.get("url")
                        if image_url:
                            sc.image_url = image_url
                            sc.image_status = 2
                            sc.finished_at = naive_now()
                            sc.image_meta = (sc.image_meta or {})
                            sc.image_meta["polled_payload"] = payload
                            db.commit()
                            polled += 1
                            continue
                        else:
                            sc.image_status = 3
                            sc.error_msg = "runninghub returned success but no file URL"
                            sc.finished_at = naive_now()
                            db.commit()
                            polled += 1
                            continue
                    elif status == "pending":
                        # nothing to update; leave as queued
                        continue
                    else:
                        sc.image_status = 3
                        sc.error_msg = service.extract_error_message(payload) or "runninghub job failed"
                        sc.finished_at = naive_now()
                        db.commit()
                        polled += 1
                        continue

                else:
                    # For other providers, attempt to instantiate service and call a generic 'get_outputs' or 'get_job_status'
                    if provider_name == "liblib":
                        service = LiblibService(db)
                    elif provider_name == "comfyui":
                        service = ComfyUIService()

                    if service is not None and hasattr(service, "get_outputs"):
                        payload = service.get_outputs(job_id)
                        # try to interpret a resource URL from payload
                        url = None
                        if isinstance(payload, dict):
                            # try common keys
                            url = payload.get("image_url") or payload.get("url") or (payload.get("data") and payload.get("data")[0].get("url") if isinstance(payload.get("data"), list) and payload.get("data") else None)
                        if url:
                            sc.image_url = url
                            sc.image_status = 2
                            sc.finished_at = naive_now()
                            sc.image_meta = (sc.image_meta or {})
                            sc.image_meta["polled_payload"] = payload
                        else:
                            # Could not find url; mark as failed
                            sc.image_status = 3
                            sc.error_msg = "polling did not return resource URL"
                            sc.finished_at = naive_now()
                        db.commit()
                        polled += 1
                        continue

            except Exception as exc:
                try:
                    sc.image_status = 3
                    sc.error_msg = str(exc)
                    sc.finished_at = naive_now()
                    db.commit()
                    polled += 1
                except Exception:
                    pass
                continue

        return {"polled": polled}
    finally:
        db.close()

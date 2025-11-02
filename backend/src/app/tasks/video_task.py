"""Celery 任务：视频生成（video_task）"""
import json
from typing import Any, Dict, Optional

from celery import shared_task
from sqlalchemy.orm import Session

from app.celery_app import celery_app
from app.database import get_db_session
from app.models.media import Scene
from app.models.task import Task, TaskStep
from app.services.providers.base import MediaRequest, VideoPromptRequest
from app.services.providers.registry import resolve_task_provider
from app.services.providers.utils import collect_provider_candidates
from app.tasks.utils import ensure_provider_map
from app.tasks.utils.interrupts import StepInterruptController, summarize_status_counts
from app.utils.timezone import naive_now


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def generate_video_task(self, task_id: int, scene_id: Optional[int] = None):
    """异步视频生成任务"""
    db: Session = get_db_session()
    try:
        task = db.get(Task, task_id)
        if not task or task.is_deleted:
            return {"error": "任务不存在"}

        step = (
            db.query(TaskStep)
            .filter(TaskStep.task_id == task_id, TaskStep.step_name == "generate_videos")
            .first()
        )
        if not step:
            return {"error": "视频生成步骤不存在"}
        step.status = 1
        db.commit()

        provider_candidates = collect_provider_candidates(task)
        provider, provider_name = resolve_task_provider("video", provider_candidates, db)
        step.provider = provider_name
        db.commit()

        try:
            prompt_provider, prompt_provider_name = resolve_task_provider(
                "video_prompt", provider_candidates, db
            )
        except ValueError:
            prompt_provider = None
            prompt_provider_name = None

        providers_map = ensure_provider_map(task.providers)
        if prompt_provider_name:
            providers_map["video_prompt"] = prompt_provider_name
        providers_map["video"] = provider_name
        task.providers = providers_map
        db.commit()

        task_config = task.task_config or {}
        if not isinstance(task_config, dict):
            task_config = {}
        video_config: Dict[str, Any] = {}
        if isinstance(task_config.get("video"), dict):
            video_config = task_config.get("video") or {}

        style_meta = task_config.get("style_meta") if isinstance(task_config.get("style_meta"), dict) else {}
        runninghub_meta = style_meta.get("runninghub") if isinstance(style_meta.get("runninghub"), dict) else {}
        runninghub_video_workflow_id = runninghub_meta.get("video_workflow_config_id")

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

        interrupt_helper = StepInterruptController(
            db=db,
            step=step,
            status_attr="video_status",
            celery_id_attr="video_celery_id",
            job_id_attr="video_job_id",
            url_attr="raw_video_url",
            extra_reset=lambda sc: setattr(sc, "video_meta", None),
            interrupt_clear_attrs=("video_celery_id", "raw_video_url"),
        )

        reset_count = interrupt_helper.reset_interrupted(target_scenes)
        if reset_count:
            self.get_logger().info("Reset %s interrupted video scenes to pending before rerun", reset_count)

        step = interrupt_helper.step
        scene_ids = [sc.id for sc in target_scenes]

        task_params = task.params if isinstance(task.params, dict) else {}
        storyboard_context = json.dumps(
            {
                "task_id": task.id,
                "description": task_params.get("description"),
                "reference_video": task_params.get("reference_video"),
                "scenes": [
                    {
                        "scene_number": sc.seq,
                        "narration": sc.narration_text,
                        "image_prompt": sc.image_prompt,
                    }
                    for sc in scenes
                ],
            },
            ensure_ascii=False,
        )

        try:
            current_task_id = str(getattr(self.request, "id", ""))
        except Exception:
            current_task_id = ""

        for scene_pk in scene_ids:
            if interrupt_helper.should_abort():
                step = interrupt_helper.step
                self.get_logger().info("Video step interrupted, aborting remaining scenes")
                break

            step = interrupt_helper.step

            scene = db.get(Scene, scene_pk)
            if not scene:
                continue

            if scene.video_status == 2 and scene.raw_video_url:
                continue

            updated = False
            if current_task_id and scene.video_celery_id != current_task_id:
                scene.video_celery_id = current_task_id
                updated = True

            if scene.video_status != 1:
                scene.video_status = 1
                scene.error_msg = None
                updated = True

            if updated:
                db.commit()
                db.refresh(scene)

            extra: Dict[str, Any] = {
                "task_id": task.id,
                "scene_seq": scene.seq,
            }
            if provider_name == "runninghub" and runninghub_video_workflow_id:
                extra["runninghub_video_workflow_config_id"] = runninghub_video_workflow_id
            if video_config.get("frame_rate") is not None:
                try:
                    extra["frame_rate"] = int(video_config.get("frame_rate"))
                except (TypeError, ValueError):
                    pass
            if video_config.get("nca_options"):
                extra["nca_options"] = video_config.get("nca_options")
            if prompt_provider_name:
                extra["video_prompt_provider"] = prompt_provider_name

            duration_source: Optional[float] = None
            if getattr(scene, "audio_duration", None) is not None:
                try:
                    duration_source = float(scene.audio_duration) if scene.audio_duration is not None else None
                except (TypeError, ValueError):
                    duration_source = None

            if duration_source is None:
                raw_config_duration = video_config.get("duration")
                try:
                    duration_source = (
                        float(raw_config_duration)
                        if raw_config_duration is not None
                        else None
                    )
                except (TypeError, ValueError):
                    duration_source = None

            rounded_duration: Optional[int] = None
            if duration_source is not None:
                if duration_source < 0:
                    duration_source = 0.0
                rounded_duration = int(round(duration_source))
                if rounded_duration <= 0 and duration_source > 0:
                    rounded_duration = 1

            if duration_source is not None:
                extra["audio_duration"] = duration_source
            if rounded_duration is not None:
                extra["duration"] = rounded_duration

            requires_prompt = provider_name in {"fal", "runninghub"}
            prompt_text = (scene.video_prompt or "").strip()

            if requires_prompt:
                if not prompt_text:
                    if not prompt_provider:
                        raise RuntimeError("缺少 video_prompt 提供商，无法生成视频提示词")
                    if not (scene.narration_text or "").strip():
                        raise RuntimeError("分镜缺少旁白内容，无法生成视频提示词")

                    prompt_request = VideoPromptRequest(
                        scene_seq=scene.seq,
                        narration=scene.narration_text or "",
                        image_prompt=scene.image_prompt,
                        image_url=scene.image_url,
                        storyboard_context=storyboard_context,
                        extra={
                            "task_id": task.id,
                            "video_provider": provider_name,
                            "target_provider": provider_name,
                            "duration": rounded_duration if rounded_duration is not None else None,
                            "audio_duration": duration_source,
                        },
                    )
                    try:
                        prompt_result = prompt_provider.generate(prompt_request)
                    except Exception as prompt_exc:  # pragma: no cover - remote failure
                        raise RuntimeError(f"视频提示词生成失败: {prompt_exc}") from prompt_exc

                    prompt_text = (prompt_result.prompt or "").strip()
                    if not prompt_text:
                        raise RuntimeError("视频提示词服务返回空结果")

                    scene.video_prompt = prompt_text
                    existing_meta = scene.video_meta if isinstance(scene.video_meta, dict) else {}
                    prompt_meta = dict(existing_meta) if isinstance(existing_meta, dict) else {}
                    prompt_meta["prompt"] = prompt_text
                    if prompt_provider_name:
                        prompt_meta["video_prompt_provider"] = prompt_provider_name
                    raw_payload = getattr(prompt_result, "raw", None)
                    if raw_payload is not None:
                        prompt_meta["prompt_raw"] = raw_payload
                    scene.video_meta = prompt_meta
                    db.commit()
                    db.refresh(scene)

            if prompt_text:
                extra["prompt"] = prompt_text
                extra["video_prompt"] = prompt_text

            if interrupt_helper.should_abort():
                step = interrupt_helper.step
                continue

            try:
                result = provider.generate(
                    MediaRequest(
                        prompt=prompt_text or None,
                        image_url=scene.image_url,
                        audio_url=scene.audio_url,
                        duration=rounded_duration,
                        extra=extra,
                    )
                )
            except Exception as exc:  # pragma: no cover - remote failure
                scene.video_status = 3
                scene.video_provider = provider_name
                scene.video_retry_count = (scene.video_retry_count or 0) + 1
                scene.raw_video_url = None
                scene.error_msg = str(exc)
                db.commit()
                continue

            scene.video_provider = provider_name
            scene.video_job_id = getattr(result, "job_id", None)

            if interrupt_helper.handle_interrupt_after_provider(scene):
                db.commit()
                step = interrupt_helper.step
                self.get_logger().info("Scene %s marked interrupted after provider response", scene_pk)
                break

            merged_meta: Dict[str, Any] = {}
            if isinstance(scene.video_meta, dict):
                merged_meta.update(scene.video_meta)
            if isinstance(result.meta, dict):
                merged_meta.update(result.meta)
            elif result.meta is not None:
                merged_meta["provider_raw"] = result.meta

            if result.status == "completed" and result.resource_url:
                raw_video_url = result.resource_url
                merged_meta["raw_video_url"] = raw_video_url
                scene.raw_video_url = raw_video_url
                scene.video_status = 2
                scene.merge_status = 0
                scene.merge_retry_count = 0
                scene.merge_video_url = None
                scene.merge_job_id = None
                scene.merge_meta = None
                scene.merge_video_provider = None
                scene.error_msg = None
            elif result.status == "queued":
                scene.video_status = 1
                scene.error_msg = None
            else:
                scene.video_status = 3
                scene.error_msg = (result.meta or {}).get("error") if isinstance(result.meta, dict) else None
                scene.video_retry_count = (scene.video_retry_count or 0) + 1
                scene.raw_video_url = None

            # clear video_celery_id for scenes that are no longer actively processing
            if getattr(scene, 'video_celery_id', None) and scene.video_status != 1:
                scene.video_celery_id = None

            scene.video_meta = merged_meta if merged_meta else None
            db.commit()

        scenes = (
            db.query(Scene)
            .filter(Scene.task_id == task_id)
            .order_by(Scene.seq.asc())
            .all()
        )

        overall_completed, overall_queued, overall_failed, pending_count = summarize_status_counts(
            scenes,
            status_attr="video_status",
        )

        step = interrupt_helper.step
        step.result = {
            "provider": provider_name,
            "video_prompt_provider": prompt_provider_name,
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
                step.error_msg = "视频生成全部失败"
                step.progress = 0
            elif overall_failed > 0 and overall_completed > 0:
                step.status = 6
                step.error_msg = "部分视频生成失败"
            elif overall_queued > 0 or pending_count > 0:
                step.status = 1
            else:
                step.status = 2

        db.commit()

        task_mode = getattr(task, "mode", None) or (task.task_config or {}).get("mode")
        if not task_mode:
            raise RuntimeError("任务未配置执行模式")
        # Only auto-continue when the step is fully completed (status == 2). Do NOT continue on INTERRUPTED (6).
        if scene_id is None and task_mode == "auto" and step.status == 2:
            try:
                celery_app.send_task(
                    "app.tasks.scene_merge_task.merge_scene_media_task",
                    args=[task.id],
                    queue="default",
                    serializer="json",
                )
            except Exception:
                pass

        return {"videos": len(target_scenes)}
    except Exception as e:
        # Roll back any pending DB state from the failing run
        try:
            db.rollback()
        except Exception:
            pass

        # Mark any scenes that were still 'processing' as failed so the UI/db
        # does not leave them stuck in state=1 after the task ultimately fails.
        try:
            in_progress_scenes = (
                db.query(Scene)
                .filter(Scene.task_id == task_id, Scene.video_status == 1)
                .all()
            )
            for sc in in_progress_scenes:
                sc.video_status = 3
                # Only set/overwrite error_msg if empty to avoid destroying prior details.
                if not (sc.error_msg or "").strip():
                    sc.error_msg = str(e)
                sc.finished_at = naive_now()
            if in_progress_scenes:
                db.commit()
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass

        # Mark the step as failed (existing behavior)
        step = (
            db.query(TaskStep)
            .filter(TaskStep.task_id == task_id, TaskStep.step_name == "generate_videos")
            .first()
        )
        if step:
            step.status = 3
            step.error_msg = str(e)
            db.commit()

        # Re-raise to preserve existing Celery retry behavior (do not change retry policy)
        raise self.retry(exc=e)
    finally:
        db.close()

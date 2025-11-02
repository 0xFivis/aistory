"""Celery 任务：分镜生成（storyboard）"""
from celery import shared_task
from sqlalchemy.orm import Session

from app.celery_app import celery_app
from app.database import get_db_session
from app.models.media import Scene
from app.models.task import Task, TaskStep
from app.services.providers.base import StoryboardRequest
from app.services.providers.registry import resolve_task_provider
from app.services.providers.utils import collect_provider_candidates
from app.tasks.utils import ensure_provider_map
from app.services.style_preset_service import merge_style_preset
from app.services.exceptions import APIException
from app.services.storyboard_script import persist_script_scenes


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def generate_storyboard_task(self, task_id: int):
    """异步分镜生成任务"""
    db: Session = get_db_session()
    try:
        task = db.get(Task, task_id)
        if not task or task.is_deleted:
            return {"error": "任务不存在"}
        # 获取分镜生成步骤
        step = db.query(TaskStep).filter(TaskStep.task_id == task_id, TaskStep.step_name == "storyboard").first()
        if not step:
            return {"error": "分镜步骤不存在"}
        # 标记步骤处理中
        step.status = 1
        db.commit()
        # 解析任务参数
        task_params = task.params or {}
        if not isinstance(task_params, dict):
            task_params = {}

        task_config = task.task_config or {}
        if not isinstance(task_config, dict):
            task_config = {}

        merged_config, storyboard_config, _ = merge_style_preset(db, task_config)
        if task_config != merged_config:
            task.task_config = merged_config
            db.commit()
        task_config = merged_config

        if not isinstance(storyboard_config, dict):
            storyboard_config = {}

        trigger_words_value = (
            storyboard_config.get("trigger_words")
            or storyboard_config.get("liblib_trigger_words")
            or task_config.get("storyboard_trigger_words")
            or task_config.get("liblib_trigger_words")
        )

        storyboard_input_mode = None
        if isinstance(storyboard_config, dict):
            storyboard_input_mode = storyboard_config.get("input_mode") or storyboard_config.get("mode")

        script_mode = False
        script_payload = None
        if isinstance(storyboard_input_mode, str) and storyboard_input_mode.lower() == "script":
            script_mode = True
        elif task_params.get("storyboard_script"):
            script_mode = True

        if script_mode:
            script_payload = task_params.get("storyboard_script")
            if not script_payload and isinstance(storyboard_config, dict):
                script_payload = storyboard_config.get("script")
            if not isinstance(script_payload, list) or not script_payload:
                raise RuntimeError("脚本模式缺少 storyboard_script 数据")

            provider_label = "script_import"
            if isinstance(storyboard_config, dict):
                raw_label = storyboard_config.get("script_provider") or storyboard_config.get("provider")
                if isinstance(raw_label, str) and raw_label.strip():
                    provider_label = raw_label.strip()

            result = persist_script_scenes(
                db=db,
                task=task,
                step=step,
                script_items=script_payload,
                provider_label=provider_label,
                allow_existing=True,
                trigger_words=trigger_words_value,
            )
            db.commit()

            task_mode = getattr(task, 'mode', None) or (task.task_config or {}).get('mode')
            if not task_mode:
                raise RuntimeError("任务未配置执行模式")
            if task_mode == 'auto' and result.created:
                celery_app.send_task('app.tasks.image_task.generate_images_task', args=[task.id], queue='default', serializer='json')

            return {"scenes": result.scene_count}

        default_word_count_strategy = "每个分镜旁白字数在4到28字之间动态变化根据内容重要性和情感节奏灵活调节"

        prompt_example = (
            storyboard_config.get("prompt_example")
            or storyboard_config.get("prompt_example_template")
            or task_config.get("storyboard_prompt_example")
            or task_config.get("liblib_prompt_example")
        )
        trigger_words = trigger_words_value
        channel_identity = storyboard_config.get("channel_identity") or task_config.get("channel_identity")
        word_count_strategy = (
            storyboard_config.get("word_count_strategy")
            or task_config.get("word_count_strategy")
            or default_word_count_strategy
        )

        # 解析并实例化提供商
        provider, provider_name = resolve_task_provider("storyboard", collect_provider_candidates(task), db)
        step.provider = provider_name
        db.commit()

        # 调用提供商生成分镜
        raw_scene_count = task_config.get("scene_count", 0)
        try:
            scene_count_value = int(raw_scene_count)
        except (TypeError, ValueError):
            scene_count_value = 0

        request = StoryboardRequest(
            video_content=task_params.get("description", ""),
            reference_video=task_params.get("reference_video"),
            scene_count=scene_count_value,
            language=task_config.get("language", "中文"),
            word_count_strategy=word_count_strategy,
            prompt_example=prompt_example,
            trigger_words=trigger_words,
            channel_identity=channel_identity,
        )
        result = provider.generate(request)

        scenes = result.scenes or []

        providers_map = ensure_provider_map(task.providers)
        providers_map["storyboard"] = provider_name
        task.providers = providers_map
        task.total_scenes = len(scenes)
        task.completed_scenes = 0

        # 保存分镜到 Scene 表
        for idx, item in enumerate(scenes, start=1):
            scene = Scene(
                task_id=task.id,
                seq=item.scene_number or idx,
                status=0,
                narration_text=item.narration,
                narration_word_count=item.narration_word_count,
                image_prompt=item.image_prompt,
                image_status=0,
                audio_status=0,
                video_status=0,
                image_retry_count=0,
                audio_retry_count=0,
                video_retry_count=0,
                params={
                    "narration": item.narration,
                    "narration_word_count": item.narration_word_count,
                    "image_prompt": item.image_prompt,
                },
                result=None,
            )
            db.add(scene)

        step.status = 2
        step.progress = 100
        step.result = {
            "provider": provider_name,
            "scene_count": len(scenes),
        }
        db.commit()

        # 如果任务为自动模式，则自动触发下一步（图片生成）
        task_mode = getattr(task, 'mode', None) or (task.task_config or {}).get('mode')
        if not task_mode:
            raise RuntimeError("任务未配置执行模式")
        if task_mode == 'auto':
            celery_app.send_task('app.tasks.image_task.generate_images_task', args=[task.id], queue='default', serializer='json')

        return {"scenes": len(scenes)}
    except APIException as exc:
        db.rollback()
        step = db.query(TaskStep).filter(TaskStep.task_id == task_id, TaskStep.step_name == "storyboard").first()
        if step:
            step.status = 3
            step.error_msg = str(exc)
            db.commit()
        raise self.retry(exc=exc)
    except Exception as e:
        db.rollback()
        # 步骤失败
        step = db.query(TaskStep).filter(TaskStep.task_id == task_id, TaskStep.step_name == "storyboard").first()
        if step:
            step.status = 3
            step.error_msg = str(e)
            db.commit()
        raise
    finally:
        db.close()

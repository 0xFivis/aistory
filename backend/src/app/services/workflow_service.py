"""工作流编排服务：负责任务步骤调度、状态管理、重试逻辑"""
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.task import Task, TaskStep
from app.models.media import Scene
from app.services.gemini_service import GeminiService
from app.services.fishaudio_service import FishAudioService
from app.services.liblib_service import LiblibService
from app.services.nca_service import NCAService
from app.services.style_preset_service import merge_style_preset
from .exceptions import APIException, ConfigurationException, ValidationException

class WorkflowService:
    """工作流编排服务"""
    def __init__(self, db: Session):
        self.db = db

    def run_step(self, task: Task, step: TaskStep) -> Dict[str, Any]:
        """执行单个任务步骤（同步版本，后续可接 Celery）"""
        # 这里只做结构示例，具体业务逻辑需根据实际需求完善
        if step.step_name == "storyboard":
            return self._run_storyboard(task, step)
        elif step.step_name == "generate_images":
            return self._run_generate_images(task, step)
        elif step.step_name == "generate_audio":
            return self._run_generate_audio(task, step)
        elif step.step_name == "generate_videos":
            return self._run_generate_videos(task, step)
        elif step.step_name == "merge_video":
            return self._run_merge_video(task, step)
        else:
            raise ValidationException(f"未知步骤: {step.step_name}")

    def _run_storyboard(self, task: Task, step: TaskStep) -> Dict[str, Any]:
        # Gemini 分镜生成
        gemini = GeminiService()
        task_params = task.params or {}
        if not isinstance(task_params, dict):
            task_params = {}

        task_config = task.task_config or {}
        if not isinstance(task_config, dict):
            task_config = {}

        merged_config, storyboard_config, preset = merge_style_preset(self.db, task_config)
        if task_config != merged_config:
            task.task_config = merged_config
            self.db.commit()
        task_config = merged_config

        word_count_strategy = (
            storyboard_config.get("word_count_strategy")
            or task_config.get("word_count_strategy")
        )
        if not word_count_strategy:
            raise ConfigurationException("word_count_strategy 未配置", service_name="Workflow")
        prompt_example = (
            storyboard_config.get("prompt_example")
            or storyboard_config.get("prompt_example_template")
            or task_config.get("storyboard_prompt_example")
            or task_config.get("liblib_prompt_example")
        )
        trigger_words = (
            storyboard_config.get("trigger_words")
            or storyboard_config.get("liblib_trigger_words")
            or task_config.get("storyboard_trigger_words")
            or task_config.get("liblib_trigger_words")
        )
        channel_identity = storyboard_config.get("channel_identity") or task_config.get("channel_identity")

        language_value = task_config.get("language")
        if not language_value:
            raise ConfigurationException("language 未配置", service_name="Workflow")

        num_scenes_value = task_config.get("scene_count")
        if num_scenes_value is None:
            raise ConfigurationException("scene_count 未配置", service_name="Workflow")

        scenes = gemini.generate_storyboard(
            video_content=task_params.get("description"),
            reference_video=task_params.get("reference_video"),
            num_scenes=num_scenes_value,
            language=language_value,
            word_count_strategy=word_count_strategy,
            prompt_example=prompt_example,
            trigger_words=trigger_words,
            channel_identity=channel_identity,
        )
        # ...保存分镜到 Scene 表...
        return {"scenes": scenes}

    def _run_generate_images(self, task: Task, step: TaskStep) -> Dict[str, Any]:
        # Liblib 图像生成
        liblib = LiblibService(self.db)
        # ...遍历分镜，生成图片...
        return {"status": "images generated"}

    def _run_generate_audio(self, task: Task, step: TaskStep) -> Dict[str, Any]:
        # Fish Audio 语音生成
        fish = FishAudioService(self.db)
        # ...遍历分镜，生成音频...
        return {"status": "audio generated"}

    def _run_generate_videos(self, task: Task, step: TaskStep) -> Dict[str, Any]:
        # NCA 视频生成
        nca = NCAService(self.db)
        # ...遍历分镜，合成视频片段...
        return {"status": "videos generated"}

    def _run_merge_video(self, task: Task, step: TaskStep) -> Dict[str, Any]:
        # NCA 视频合并
        nca = NCAService(self.db)
        # ...合并所有片段...
        return {"status": "video merged"}

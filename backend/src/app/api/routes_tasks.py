from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, AliasChoices, ConfigDict, model_validator
from sqlalchemy import or_
from sqlalchemy.orm import Session
from typing import Optional, List, Any, Dict
from datetime import datetime

from app.utils.timezone import naive_now, to_local

from app.database import get_db
from app.models.task import Task, TaskStep
from app.models.media import Scene
from app.models import MediaAsset, ServiceOption, SubtitleStyle, SubtitleDocument
from app.services.gemini_service import GeminiService
from app.services.exceptions import ServiceException
from app.celery_app import celery_app
from app.tasks.utils import ensure_provider_map
from app.services.storage_service import StorageService
from app.services.storyboard_script import persist_script_scenes
from app.services.style_preset_service import merge_style_preset
from app.services.subtitle_style_service import SubtitleStyleService
from app.services.tasks.reset_service import TaskResetError, reset_task_audio_pipeline
from fastapi import Body

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


_storage_service = StorageService()
_subtitle_style_service = SubtitleStyleService()


DEFAULT_TASK_STEPS: List[Dict[str, Any]] = [
    {"step_name": "storyboard", "seq": 1, "max_retries": 3},
    {"step_name": "generate_images", "seq": 2, "max_retries": 3},
    {"step_name": "generate_audio", "seq": 3, "max_retries": 3},
    {"step_name": "generate_videos", "seq": 4, "max_retries": 3},
    {"step_name": "merge_scene_media", "seq": 5, "max_retries": 3},
    {"step_name": "merge_video", "seq": 6, "max_retries": 3},
    {"step_name": "finalize_video", "seq": 7, "max_retries": 3},
]


def _external_url(value: Optional[str]) -> Optional[str]:
    return _storage_service.get_external_url(value)


def _strip_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _serialize_task(task: Task) -> Dict[str, Any]:
    data = {
        "id": task.id,
        "workflow_type": task.workflow_type,
        "status": task.status,
        "progress": task.progress,
        "total_scenes": task.total_scenes,
        "completed_scenes": task.completed_scenes,
        "params": task.params,
        "result": task.result,
        "task_config": task.task_config,
        "error_msg": task.error_msg,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
        "mode": getattr(task, "mode", "auto"),
        "providers": getattr(task, "providers", None),
        "merged_video_url": getattr(task, "merged_video_url", None),
        "final_video_url": getattr(task, "final_video_url", None),
        "selected_voice_id": getattr(task, "selected_voice_id", None),
        "selected_voice_name": getattr(task, "selected_voice_name", None),
        "subtitle_style_id": getattr(task, "subtitle_style_id", None),
        "subtitle_style_snapshot": getattr(task, "subtitle_style_snapshot", None),
    }
    if data["merged_video_url"]:
        data["merged_video_url"] = _external_url(data["merged_video_url"]) or data["merged_video_url"]
    if data["final_video_url"]:
        data["final_video_url"] = _external_url(data["final_video_url"]) or data["final_video_url"]
    data["created_at"] = to_local(data.get("created_at"))
    data["updated_at"] = to_local(data.get("updated_at"))
    return data


def _build_subtitle_style_snapshot(style: SubtitleStyle) -> Dict[str, Any]:
    """将字幕样式实体转换为可序列化的快照。"""
    created_at = style.created_at.isoformat() if style.created_at else None
    updated_at = style.updated_at.isoformat() if style.updated_at else None
    style_fields, script_settings, effect_settings = _subtitle_style_service.split_sections(style.style_payload)
    style_payload = style.style_payload if isinstance(style.style_payload, dict) else {}
    snapshot: Dict[str, Any] = {
        "id": style.id,
        "name": style.name,
        "description": style.description,
        "style_fields": style_fields,
        "script_settings": script_settings,
        "effect_settings": effect_settings,
        "style": style_fields or style_payload,
        "style_payload": style_payload,
        "sample_text": style.sample_text,
        "is_active": bool(style.is_active),
        "is_default": bool(getattr(style, "is_default", False)),
    }
    if created_at:
        snapshot["created_at"] = created_at
    if updated_at:
        snapshot["updated_at"] = updated_at
    return snapshot


def _serialize_scene(scene: Scene) -> Dict[str, Any]:
    data = {
        "id": scene.id,
        "task_id": scene.task_id,
        "seq": scene.seq,
        "status": scene.status,
        "narration_text": scene.narration_text,
        "narration_word_count": scene.narration_word_count,
        "image_prompt": scene.image_prompt,
        "video_prompt": getattr(scene, "video_prompt", None),
        "image_status": scene.image_status,
        "audio_status": scene.audio_status,
        "video_status": scene.video_status,
        "merge_status": getattr(scene, "merge_status", 0),
        "image_url": scene.image_url,
        "audio_url": scene.audio_url,
        "audio_duration": getattr(scene, "audio_duration", None),
        "merge_video_url": getattr(scene, "merge_video_url", None),
        "raw_video_url": getattr(scene, "raw_video_url", None),
        "image_meta": getattr(scene, "image_meta", None),
        "audio_meta": getattr(scene, "audio_meta", None),
        "video_meta": getattr(scene, "video_meta", None),
        "merge_meta": getattr(scene, "merge_meta", None),
        "merge_video_provider": getattr(scene, "merge_video_provider", None),
        "image_retry_count": scene.image_retry_count,
        "audio_retry_count": scene.audio_retry_count,
        "video_retry_count": scene.video_retry_count,
        "merge_retry_count": getattr(scene, "merge_retry_count", 0),
        "params": scene.params,
        "result": scene.result,
        "error_msg": scene.error_msg,
        "started_at": scene.started_at,
        "finished_at": scene.finished_at,
    }
    if data["audio_url"]:
        data["audio_url"] = _external_url(data["audio_url"]) or data["audio_url"]
    if data["merge_video_url"]:
        data["merge_video_url"] = _external_url(data["merge_video_url"]) or data["merge_video_url"]
    data["started_at"] = to_local(data.get("started_at"))
    data["finished_at"] = to_local(data.get("finished_at"))
    return data


def _serialize_subtitle_document(document: SubtitleDocument) -> Dict[str, Any]:
    segments = document.segments if isinstance(document.segments, list) else []
    info = document.info if isinstance(document.info, dict) else document.info
    options = document.options if isinstance(document.options, dict) else document.options
    text = document.text or ""
    preview = text.strip()[:200]
    if not preview and isinstance(info, dict):
        preview_candidate = str(info.get("text_preview") or "").strip()
        if preview_candidate:
            preview = preview_candidate[:200]

    srt_api_path = document.srt_api_path
    ass_api_path = document.ass_api_path

    payload: Dict[str, Any] = {
        "id": document.id,
        "task_id": document.task_id,
        "language": document.language,
        "model_name": document.model_name,
        "text": text,
        "segment_count": document.segment_count,
        "segments": segments,
        "info": info,
        "options": options,
        "srt_api_path": srt_api_path,
        "srt_relative_path": document.srt_relative_path,
        "srt_public_url": document.srt_public_url or _storage_service.get_external_url(srt_api_path),
        "ass_api_path": ass_api_path,
        "ass_relative_path": document.ass_relative_path,
        "ass_public_url": document.ass_public_url or _storage_service.get_external_url(ass_api_path),
        "created_at": to_local(document.created_at),
        "updated_at": to_local(document.updated_at),
    }
    if preview:
        payload["text_preview"] = preview
    return payload


def ensure_task_steps(db: Session, task_id: int) -> List[TaskStep]:
    """确保任务包含所有默认步骤，并将旧任务的顺序同步到最新流程"""
    existing_steps = db.query(TaskStep).filter(TaskStep.task_id == task_id).all()
    existing_map = {step.step_name: step for step in existing_steps}

    changed = False
    for cfg in DEFAULT_TASK_STEPS:
        step = existing_map.get(cfg["step_name"])
        if not step:
            step = TaskStep(
                task_id=task_id,
                step_name=cfg["step_name"],
                seq=cfg["seq"],
                status=0,
                progress=0,
                retry_count=0,
                max_retries=cfg["max_retries"],
            )
            db.add(step)
            existing_steps.append(step)
            existing_map[step.step_name] = step
            changed = True
        else:
            if step.seq != cfg["seq"]:
                step.seq = cfg["seq"]
                changed = True
            if step.max_retries != cfg["max_retries"]:
                step.max_retries = cfg["max_retries"]
                changed = True

    if changed:
        db.commit()
        existing_steps = (
            db.query(TaskStep)
            .filter(TaskStep.task_id == task_id)
            .order_by(TaskStep.seq.asc(), TaskStep.id.asc())
            .all()
        )
    else:
        existing_steps.sort(key=lambda s: (s.seq, s.id))

    return existing_steps


class TaskConfigModel(BaseModel):
    """任务配置模型"""
    gemini_api_key: Optional[str] = Field(None, description="Gemini API Key (可选，默认从数据库读取)")
    audio_voice_id: Optional[str] = Field(
        None,
        description="音频生成 voice 选项 ID",
    )
    audio_voice_name: Optional[str] = Field(
        None,
        description="音频生成 voice 名称（可选）",
    )
    audio_voice_value: Optional[str] = Field(
        None,
        description="音频生成 voice 实际 ID（内部使用）",
    )
    audio_voice_service: Optional[str] = Field(
        default="fishaudio",
        description="音频生成服务名称，默认为 fishaudio",
    )
    audio_trim_silence: Optional[bool] = Field(
        default=True,
        description="是否在生成音频后自动裁剪首尾静音",
    )
    lora_id: Optional[str] = Field(None, description="LoRA ID", alias="liblib_lora_id")
    checkpoint_id: Optional[str] = Field(
        None,
        description="主模型ID",
        alias="liblib_model_id",
        validation_alias=AliasChoices("checkpoint_id", "model_id", "liblib_model_id"),
    )
    style_preset_id: Optional[int] = Field(None, description="风格预设 ID")
    bgm_asset_id: Optional[int] = Field(None, description="背景音乐素材ID")
    nca_api_key: Optional[str] = Field(None, description="NCA API Key (可选)")
    fal_api_key: Optional[str] = Field(None, description="Fal API Key (可选)")
    scene_count: int = Field(
        0,
        ge=0,
        le=1000,
        description="分镜数量，0 表示根据模型自动决定",
    )
    language: str = Field(..., description="旁白语言")
    provider: Optional[str] = Field(None, description="优先图片/视频生成服务提供商")
    providers: Optional[Dict[str, str]] = Field(
        default=None,
        description="分步骤服务提供商映射，例如 {'image': 'comfyui', 'video': 'nca'}",
    )
    storyboard: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Storyboard 额外配置（可包含 style_preset_id 等自定义字段）",
    )
    finalize: Optional[Dict[str, Any]] = Field(
        default=None,
        description="最终成片配置（包括字幕、配乐等）",
    )
    subtitle_style_id: Optional[int] = Field(
        None,
        description="关联的字幕样式 ID",
    )

    model_config = ConfigDict(populate_by_name=True, protected_namespaces=())


class StoryboardScriptSceneModel(BaseModel):
    scene_number: int = Field(
        ...,
        description="分镜编号",
        validation_alias=AliasChoices("scene_number", "sceneNumber", "分镜编号"),
    )
    name: Optional[str] = Field(
        None,
        description="分镜名称",
        validation_alias=AliasChoices("scene_name", "sceneName", "分镜名称"),
    )
    visual: str = Field(
        ...,
        description="分镜画面描述",
        validation_alias=AliasChoices("visual", "vision", "分镜画面"),
    )
    animation: Optional[str] = Field(
        None,
        description="分镜动画/动作",
        validation_alias=AliasChoices("animation", "motion", "分镜动画"),
    )
    narration: Optional[str] = Field(
        None,
        description="分镜旁白",
        validation_alias=AliasChoices("narration", "voiceover", "分镜旁白"),
    )
    dialogue: Optional[str] = Field(
        None,
        description="人物话语",
        validation_alias=AliasChoices("dialogue", "lines", "分镜人物话语"),
    )

    model_config = ConfigDict(populate_by_name=True, protected_namespaces=(), extra="allow")


class StoryboardScriptPayload(BaseModel):
    script: List[StoryboardScriptSceneModel] = Field(..., description="分镜脚本数组")

    model_config = ConfigDict(populate_by_name=True, protected_namespaces=())


class CreateTaskRequest(BaseModel):
    title: str = Field(..., description="任务标题")
    description: str = Field(..., description="视频文案/描述")
    video_content: Optional[str] = Field(None, description="视频内容（兼容旧版）")
    reference_video: Optional[str] = Field(None, description="参考视频URL或描述")
    task_config: TaskConfigModel = Field(..., description="任务配置")
    
    # 兼容旧版参数
    num_scenes: Optional[int] = Field(None, description="分镜数量（已废弃，使用 task_config.scene_count）")
    language: Optional[str] = Field(None, description="旁白语言（已废弃，使用 task_config.language）")
    provider: Optional[str] = Field(None, description="提供商（已废弃，使用 task_config.provider）")
    # 执行模式：'auto' | 'manual'
    mode: Optional[str] = Field(None, description="执行模式：'auto' 或 'manual'，默认 auto")


class UpdateTaskRequest(BaseModel):
    """任务配置更新模型"""

    title: Optional[str] = Field(None, description="任务标题")
    description: Optional[str] = Field(None, description="视频文案/描述")
    reference_video: Optional[str] = Field(None, description="参考视频URL")
    mode: Optional[str] = Field(None, description="执行模式：'auto' 或 'manual'")
    scene_count: Optional[int] = Field(
        None,
        ge=0,
        le=1000,
        description="分镜数量，0 表示根据模型自动决定",
    )
    language: Optional[str] = Field(None, description="旁白语言")
    audio_voice_id: Optional[str] = Field(None, description="音频生成 voice 选项 ID（可选）")
    audio_voice_service: Optional[str] = Field(
        None,
        description="音频生成服务名称（可选）",
    )
    provider: Optional[str | None] = Field(None, description="默认图生视频提供商")
    media_tool: Optional[str | None] = Field(
        None,
        description="媒体处理工具（scene_merge/media_compose/finalize 使用的 provider）",
    )
    style_preset_id: Optional[int | None] = Field(None, description="风格组合 ID")
    bgm_asset_id: Optional[int] = Field(None, description="背景音乐素材ID")
    audio_trim_silence: Optional[bool] = Field(None, description="是否裁剪音频首尾静音")
    providers: Optional[Dict[str, str]] = Field(
        None,
        description="覆盖 provider 映射，例如 {'image': 'runninghub'}",
    )
    subtitle_style_id: Optional[int | None] = Field(
        None,
        description="覆盖任务使用的字幕样式 ID，传 null 取消样式",
    )


class TaskOut(BaseModel):
    class Config:
        from_attributes = True
    id: int
    workflow_type: str
    status: int
    progress: int
    total_scenes: Optional[int]
    completed_scenes: int
    params: Optional[Dict[str, Any]]
    result: Optional[Dict[str, Any]]
    task_config: Optional[Dict[str, Any]]
    error_msg: Optional[str]
    created_at: datetime
    updated_at: datetime
    mode: str
    providers: Optional[Dict[str, Any]] = None
    merged_video_url: Optional[str] = None
    final_video_url: Optional[str] = None
    selected_voice_id: Optional[str] = None
    selected_voice_name: Optional[str] = None
    subtitle_style_id: Optional[int] = None
    subtitle_style_snapshot: Optional[Dict[str, Any]] = None

    @model_validator(mode="before")
    @classmethod
    def _apply_timezone(cls, values):
        if isinstance(values, dict):
            values = dict(values)
            values["created_at"] = to_local(values.get("created_at"))
            values["updated_at"] = to_local(values.get("updated_at"))
            return values
        if hasattr(values, "created_at"):
            setattr(values, "created_at", to_local(getattr(values, "created_at")))
        if hasattr(values, "updated_at"):
            setattr(values, "updated_at", to_local(getattr(values, "updated_at")))
        return values


class SceneOut(BaseModel):
    class Config:
        from_attributes = True
    id: int
    task_id: int
    seq: int
    status: int
    narration_text: Optional[str]
    narration_word_count: Optional[int]
    image_prompt: Optional[str]
    video_prompt: Optional[str]
    image_status: int
    audio_status: int
    video_status: int
    merge_status: int
    image_url: Optional[str]
    audio_url: Optional[str]
    merge_video_url: Optional[str]
    raw_video_url: Optional[str] = None
    image_meta: Optional[Dict[str, Any]] = None
    audio_meta: Optional[Dict[str, Any]] = None
    video_meta: Optional[Dict[str, Any]] = None
    merge_meta: Optional[Dict[str, Any]] = None
    merge_video_provider: Optional[str] = None
    image_retry_count: int
    audio_retry_count: int
    video_retry_count: int
    merge_retry_count: int
    params: Optional[Dict[str, Any]]
    result: Optional[Dict[str, Any]]
    error_msg: Optional[str]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]

    @model_validator(mode="before")
    @classmethod
    def _apply_timezone(cls, values):
        if isinstance(values, dict):
            values = dict(values)
            values["started_at"] = to_local(values.get("started_at"))
            values["finished_at"] = to_local(values.get("finished_at"))
            return values
        if hasattr(values, "started_at"):
            setattr(values, "started_at", to_local(getattr(values, "started_at")))
        if hasattr(values, "finished_at"):
            setattr(values, "finished_at", to_local(getattr(values, "finished_at")))
        return values


class TaskStepOut(BaseModel):
    class Config:
        from_attributes = True
    id: int
    task_id: int
    step_name: str
    seq: int
    status: int
    progress: int
    retry_count: int
    max_retries: int
    params: Optional[Dict[str, Any]]
    result: Optional[Dict[str, Any]]
    error_msg: Optional[str]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]

    @model_validator(mode="before")
    @classmethod
    def _apply_timezone(cls, values):
        if isinstance(values, dict):
            values = dict(values)
            values["started_at"] = to_local(values.get("started_at"))
            values["finished_at"] = to_local(values.get("finished_at"))
            return values
        if hasattr(values, "started_at"):
            setattr(values, "started_at", to_local(getattr(values, "started_at")))
        if hasattr(values, "finished_at"):
            setattr(values, "finished_at", to_local(getattr(values, "finished_at")))
        return values


class SubtitleDocumentOut(BaseModel):
    id: int
    task_id: int
    language: Optional[str] = None
    model_name: Optional[str] = None
    text: Optional[str] = None
    text_preview: Optional[str] = None
    segment_count: int
    segments: List[Dict[str, Any]]
    info: Optional[Dict[str, Any]] = None
    options: Optional[Dict[str, Any]] = None
    srt_api_path: Optional[str] = None
    srt_relative_path: Optional[str] = None
    srt_public_url: Optional[str] = None
    ass_api_path: Optional[str] = None
    ass_relative_path: Optional[str] = None
    ass_public_url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(protected_namespaces=())


class TaskDetailOut(BaseModel):
    """任务详情（包含步骤和分镜）"""
    class Config:
        from_attributes = True
    task: TaskOut
    steps: List[TaskStepOut]
    scenes: List[SceneOut]
    subtitle_document: Optional[SubtitleDocumentOut] = None


class VoiceOptionOut(BaseModel):
    id: int
    service_name: str
    option_type: str
    option_key: str
    option_value: str
    option_name: Optional[str] = None
    description: Optional[str] = None
    is_default: bool
    is_active: bool
    meta_data: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


@router.get("/voice-options", response_model=List[VoiceOptionOut])
def list_voice_options(
    service_name: str = Query("fishaudio", description="服务名称，默认 fishaudio"),
    option_type: str = Query("voice_id", description="选项类型，默认 voice_id"),
    include_inactive: bool = Query(False, description="是否返回已禁用的选项"),
    db: Session = Depends(get_db),
):
    """获取指定服务的语音选项列表"""

    query = db.query(ServiceOption).filter(
        ServiceOption.service_name == service_name,
        ServiceOption.option_type == option_type,
    )

    if not include_inactive:
        query = query.filter(ServiceOption.is_active == True)  # noqa: E712

    options = (
        query.order_by(
            ServiceOption.is_default.desc(),
            ServiceOption.option_name.asc(),
            ServiceOption.option_key.asc(),
        ).all()
    )

    return options



 



@router.post("/{task_id}/steps/{step_name}/interrupt")
def interrupt_step(task_id: int, step_name: str, db: Session = Depends(get_db)):
    """Interrupt a running step: revoke local celery tasks for associated scenes and mark scenes/step as INTERRUPTED (6).

    This is best-effort: revoke attempts to terminate local worker tasks. Provider-side jobs are not re-created; canceling provider jobs is provider-dependent and not handled here.
    """
    task = db.get(Task, task_id)
    if not task or task.is_deleted:
        raise HTTPException(status_code=404, detail="task not found")

    step = db.query(TaskStep).filter(TaskStep.task_id == task_id, TaskStep.step_name == step_name).first()
    if not step:
        raise HTTPException(status_code=404, detail="step not found")

    # only allow interrupting when running
    if step.status != 1:
        raise HTTPException(status_code=400, detail="step not running")

    scenes = db.query(Scene).filter(Scene.task_id == task_id).all()
    revoked = []
    affected = []
    from app.celery_app import celery_app as _celery_app
    # try to revoke step-level external task id if present
    try:
        if getattr(step, 'external_task_id', None):
            try:
                _celery_app.control.revoke(step.external_task_id, terminate=True, signal='SIGTERM')
            except Exception:
                pass
    except Exception:
        pass
    for sc in scenes:
        try:
            if sc.image_status == 1 or sc.image_celery_id:
                # attempt to revoke local celery task if we recorded an id
                task_id_str = getattr(sc, 'image_celery_id', None)
                if task_id_str:
                    try:
                        _celery_app.control.revoke(task_id_str, terminate=True, signal='SIGTERM')
                    except Exception:
                        # best-effort: ignore individual revoke failures
                        pass
                # mark scene as interrupted and clear celery id
                sc.image_status = 6
                sc.image_celery_id = None
                sc.finished_at = naive_now()
                sc.error_msg = (sc.error_msg or '') + ' [interrupted]'
                affected.append(sc.id)
            # also handle video generation interrupt
            if sc.video_status == 1 or getattr(sc, 'video_celery_id', None):
                task_id_str = getattr(sc, 'video_celery_id', None)
                if task_id_str:
                    try:
                        _celery_app.control.revoke(task_id_str, terminate=True, signal='SIGTERM')
                    except Exception:
                        pass
                sc.video_status = 6
                sc.video_celery_id = None
                sc.finished_at = naive_now()
                sc.error_msg = (sc.error_msg or '') + ' [interrupted]'
                affected.append(sc.id)
        except Exception:
            continue

    # mark the step as interrupted
    step.status = 6
    step.finished_at = naive_now()
    step.error_msg = (step.error_msg or '') + ' [interrupted]'
    db.commit()

    return {"status": "interrupted", "revoked_scenes": revoked or affected, "affected_scenes": affected}




    scenes: List[SceneOut]


@router.post("/", response_model=TaskOut)
def create_task(payload: CreateTaskRequest, db: Session = Depends(get_db)):
    """创建新任务（支持完整配置系统）"""
    
    # 兼容旧版参数
    video_content = payload.video_content or payload.description
    scene_count = payload.task_config.scene_count
    language = payload.task_config.language
    
    # 1) 创建任务
    task_config_data = payload.task_config.model_dump(exclude_none=True)
    if "audio_trim_silence" in task_config_data:
        task_config_data["audio_trim_silence"] = bool(task_config_data["audio_trim_silence"])
    else:
        task_config_data["audio_trim_silence"] = True
    bgm_asset_id = task_config_data.get("bgm_asset_id")
    if bgm_asset_id is not None:
        bgm_asset = db.get(MediaAsset, bgm_asset_id)
        if not bgm_asset or bgm_asset.asset_type != "bgm":
            raise HTTPException(status_code=400, detail="背景音乐素材不存在")
        if not bgm_asset.is_active:
            raise HTTPException(status_code=400, detail="背景音乐素材已禁用")
    provider_map_initial = ensure_provider_map(task_config_data.get("providers"))
    if provider_map_initial:
        task_config_data["providers"] = provider_map_initial
    else:
        task_config_data.pop("providers", None)

    subtitle_style_snapshot: Optional[Dict[str, Any]] = None
    subtitle_style_id_value = task_config_data.get("subtitle_style_id")
    if subtitle_style_id_value is not None:
        try:
            subtitle_style_id_value = int(subtitle_style_id_value)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="字幕样式 ID 无效")

        style_obj = db.get(SubtitleStyle, subtitle_style_id_value)
        if not style_obj or not style_obj.is_active:
            raise HTTPException(status_code=400, detail="字幕样式不存在或已禁用")

        subtitle_style_snapshot = _build_subtitle_style_snapshot(style_obj)
        task_config_data["subtitle_style_id"] = subtitle_style_id_value

        finalize_cfg_raw = task_config_data.get("finalize")
        finalize_cfg = finalize_cfg_raw if isinstance(finalize_cfg_raw, dict) else {}
        subtitles_cfg = finalize_cfg.get("subtitles") if isinstance(finalize_cfg.get("subtitles"), dict) else {}
        subtitles_cfg.setdefault("enabled", True)
        subtitles_cfg.setdefault("embed", True)
        if not subtitles_cfg.get("style"):
            subtitles_cfg["style"] = subtitle_style_snapshot.get("style")
        subtitles_cfg["style_id"] = subtitle_style_snapshot.get("id")
        subtitles_cfg["style_name"] = subtitle_style_snapshot.get("name")
        finalize_cfg["subtitles"] = subtitles_cfg
        task_config_data["finalize"] = finalize_cfg
    else:
        task_config_data.pop("subtitle_style_id", None)

    # 处理音色选择（支持 option_key 或实际 voice_id）
    selected_voice_id: Optional[str] = None
    selected_voice_name: Optional[str] = None

    voice_service_raw = task_config_data.get("audio_voice_service")
    voice_service = (
        voice_service_raw.strip()
        if isinstance(voice_service_raw, str)
        else voice_service_raw
    ) or "fishaudio"

    voice_candidate_raw = (
        task_config_data.get("audio_voice_id")
        or task_config_data.get("audio_voice_value")
        or task_config_data.get("voice_id")
    )
    voice_candidate = (
        voice_candidate_raw.strip()
        if isinstance(voice_candidate_raw, str)
        else voice_candidate_raw
    )

    if not voice_candidate:
        raise HTTPException(status_code=400, detail="必须在任务配置中指定音频音色")

    voice_option = (
        db.query(ServiceOption)
        .filter(
            ServiceOption.service_name == voice_service,
            ServiceOption.option_type == "voice_id",
            or_(
                ServiceOption.option_key == voice_candidate,
                ServiceOption.option_value == voice_candidate,
            ),
        )
        .first()
    )
    if not voice_option:
        raise HTTPException(status_code=400, detail="未找到匹配的音频音色配置")

    selected_voice_id = voice_option.option_value
    selected_voice_name = voice_option.option_name or voice_option.option_value
    task_config_data["audio_voice_id"] = voice_option.option_key
    task_config_data["audio_voice_name"] = voice_option.option_name or voice_option.option_key
    task_config_data["audio_voice_value"] = selected_voice_id
    task_config_data["audio_voice_service"] = voice_service

    task = Task(
        workflow_type="video_generation",
        status=0,
        progress=0,
        total_scenes=int(scene_count) if isinstance(scene_count, (int, float)) and int(scene_count) > 0 else None,
        completed_scenes=0,
        params={
            "title": payload.title,
            "description": payload.description,
            "reference_video": payload.reference_video,
        },
        task_config=task_config_data,
        providers=provider_map_initial or None,
        selected_voice_id=selected_voice_id,
        selected_voice_name=selected_voice_name,
        subtitle_style_id=subtitle_style_id_value,
        subtitle_style_snapshot=subtitle_style_snapshot,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # 2) 创建任务步骤（工作流编排）
    for step_cfg in DEFAULT_TASK_STEPS:
        step = TaskStep(
            task_id=task.id,
            step_name=step_cfg["step_name"],
            seq=step_cfg["seq"],
            status=0,
            progress=0,
            retry_count=0,
            max_retries=step_cfg["max_retries"],
        )
        db.add(step)
    db.commit()

    # 3) 调用 Gemini 生成分镜并保存为 scenes（MVP：同步生成，后续改为 Celery 异步）
    try:
        storyboard_step = db.query(TaskStep).filter(
            TaskStep.task_id == task.id, 
            TaskStep.step_name == "storyboard"
        ).first()
        
        # 根据模式决定是否自动入队
        mode_value = payload.mode or (task.task_config or {}).get("mode")
        if not mode_value:
            raise HTTPException(status_code=400, detail="任务缺少执行模式配置")
        task.mode = mode_value
        db.commit()

        if task.mode == "auto":
            task.status = 1
            task.progress = 10
            storyboard_step.status = 1
            storyboard_step.started_at = naive_now()
            db.commit()

            from app.celery_app import celery_app

            celery_app.send_task(
                "app.tasks.storyboard_task.generate_storyboard_task",
                args=[task.id],
                queue="default",
                serializer="json",
            )

            db.refresh(task)
        else:
            # 手动模式保持待处理状态，等待 UI 触发
            storyboard_step.status = 0
            storyboard_step.started_at = None
            task.status = 0
            task.progress = 0
            db.commit()
            db.refresh(task)
        
    except ServiceException as e:
        task.status = 3
        task.error_msg = e.message
        storyboard_step.status = 3
        storyboard_step.error_msg = e.message
        storyboard_step.finished_at = naive_now()
        db.commit()
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        task.status = 3
        task.error_msg = str(e)
        storyboard_step.status = 3
        storyboard_step.error_msg = str(e)
        storyboard_step.finished_at = naive_now()
        db.commit()
        raise HTTPException(status_code=500, detail="分镜生成失败")

    return task


@router.post("/{task_id}/storyboard/script")
def import_storyboard_script(
    task_id: int,
    payload: StoryboardScriptPayload,
    auto_trigger: bool = Query(True, description="导入成功后是否自动触发下一步骤（仅 auto 模式生效）"),
    db: Session = Depends(get_db),
):
    """导入外部分镜脚本，直接写入 Scene 并跳过大模型分镜生成。"""

    task = db.get(Task, task_id)
    if not task or task.is_deleted:
        raise HTTPException(status_code=404, detail="任务不存在")

    steps = ensure_task_steps(db, task_id)
    storyboard_step = next((step for step in steps if step.step_name == "storyboard"), None)
    if storyboard_step is None:
        raise HTTPException(status_code=400, detail="任务缺少分镜步骤")

    existing_count = (
        db.query(Scene)
        .filter(Scene.task_id == task_id)
        .count()
    )
    if existing_count:
        raise HTTPException(status_code=409, detail="任务已存在分镜，请先重置后再导入脚本")

    normalized_items: List[Dict[str, Any]] = []
    raw_items: List[Dict[str, Any]] = []
    for entry in payload.script:
        extras = getattr(entry, "model_extra", None)
        raw_entry = entry.model_dump(by_alias=True, exclude_none=True)
        normalized_items.append(
            {
                "scene_number": entry.scene_number,
                "title": _strip_text(entry.name),
                "visual": _strip_text(entry.visual),
                "animation": _strip_text(entry.animation),
                "narration": _strip_text(entry.narration),
                "dialogue": _strip_text(entry.dialogue),
                "extras": dict(extras) if extras else None,
                "raw": raw_entry,
            }
        )
        raw_items.append(raw_entry)

    if not normalized_items:
        raise HTTPException(status_code=400, detail="脚本内容为空")

    params = dict(task.params or {})
    params["storyboard_script"] = normalized_items
    params["storyboard_script_raw"] = raw_items
    task.params = params

    task_config = dict(task.task_config or {})
    merged_config, merged_storyboard_cfg, _ = merge_style_preset(db, task_config)
    task_config = merged_config
    storyboard_cfg = dict(merged_storyboard_cfg or {})
    storyboard_cfg["input_mode"] = "script"
    storyboard_cfg["source"] = "manual_script"
    storyboard_cfg["scene_count"] = len(normalized_items)
    task_config["storyboard"] = storyboard_cfg
    task.task_config = task_config

    provider_label = str(storyboard_cfg.get("script_provider") or "script_import").strip() or "script_import"
    trigger_words = (
        storyboard_cfg.get("trigger_words")
        or storyboard_cfg.get("liblib_trigger_words")
        or task_config.get("storyboard_trigger_words")
        or task_config.get("liblib_trigger_words")
    )

    try:
        result = persist_script_scenes(
            db=db,
            task=task,
            step=storyboard_step,
            script_items=normalized_items,
            provider_label=provider_label,
            allow_existing=False,
            trigger_words=trigger_words,
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))

    scene_count = result.scene_count

    task_mode = getattr(task, "mode", None) or task_config.get("mode")
    if task_mode == "auto":
        task.status = 1
        if not task.progress or task.progress < 10:
            task.progress = 10

    db.commit()

    auto_dispatched = False
    if auto_trigger and task_mode == "auto" and result.created:
        try:
            celery_app.send_task(
                "app.tasks.image_task.generate_images_task",
                args=[task.id],
                queue="default",
                serializer="json",
            )
            auto_dispatched = True
        except Exception:
            auto_dispatched = False

    return {
        "task_id": task.id,
        "scene_count": scene_count,
        "provider": provider_label,
        "auto_mode": task_mode,
        "auto_dispatched": auto_dispatched,
    }


@router.patch("/{task_id}", response_model=TaskDetailOut)
def update_task(task_id: int, payload: UpdateTaskRequest, db: Session = Depends(get_db)):
    """更新任务的基础信息与部分配置"""

    task = db.get(Task, task_id)
    if not task or task.is_deleted:
        raise HTTPException(status_code=404, detail="任务不存在")

    fields_set = getattr(payload, "model_fields_set", set())

    # ---- 更新 params ----
    params = dict(task.params or {})
    params_changed = False
    if "title" in fields_set and payload.title is not None:
        params["title"] = payload.title
        params_changed = True
    if "description" in fields_set and payload.description is not None:
        params["description"] = payload.description
        params_changed = True
    if "reference_video" in fields_set:
        params["reference_video"] = payload.reference_video
        params_changed = True
    if params_changed:
        task.params = params

    # ---- 更新 mode ----
    if "mode" in fields_set:
        if payload.mode not in {"auto", "manual"}:
            raise HTTPException(status_code=400, detail="mode 必须为 'auto' 或 'manual'")
        task.mode = payload.mode

    # ---- 更新任务配置 ----
    task_config = dict(task.task_config or {})
    config_changed = False

    if "scene_count" in fields_set and payload.scene_count is not None:
        task_config["scene_count"] = payload.scene_count
        if payload.scene_count > 0:
            task.total_scenes = payload.scene_count
            if task.completed_scenes and payload.scene_count is not None:
                task.completed_scenes = min(task.completed_scenes, payload.scene_count)
        else:
            task.total_scenes = None
        config_changed = True

    if "language" in fields_set and payload.language is not None:
        task_config["language"] = payload.language
        config_changed = True

    if "audio_trim_silence" in fields_set:
        value = payload.audio_trim_silence
        if value is None:
            task_config.pop("audio_trim_silence", None)
        else:
            task_config["audio_trim_silence"] = bool(value)
        config_changed = True

    if "style_preset_id" in fields_set:
        task_config["style_preset_id"] = payload.style_preset_id
        config_changed = True

    if "bgm_asset_id" in fields_set:
        if payload.bgm_asset_id is None:
            task_config.pop("bgm_asset_id", None)
        else:
            bgm_asset = db.get(MediaAsset, payload.bgm_asset_id)
            if not bgm_asset or bgm_asset.asset_type != "bgm":
                raise HTTPException(status_code=400, detail="背景音乐素材不存在")
            if not bgm_asset.is_active:
                raise HTTPException(status_code=400, detail="背景音乐素材已禁用")
            task_config["bgm_asset_id"] = payload.bgm_asset_id
        config_changed = True

    if "provider" in fields_set:
        provider_value = (payload.provider or None)
        task_config["provider"] = provider_value
        config_changed = True

    voice_service = str(task_config.get("audio_voice_service") or "fishaudio").strip() or "fishaudio"

    if "audio_voice_service" in fields_set:
        service_value_raw = payload.audio_voice_service
        voice_service = (
            service_value_raw.strip()
            if isinstance(service_value_raw, str)
            else service_value_raw
        ) or "fishaudio"
        task_config["audio_voice_service"] = voice_service
        config_changed = True

    if "audio_voice_id" in fields_set:
        voice_candidate_raw = payload.audio_voice_id
        voice_candidate = (
            voice_candidate_raw.strip()
            if isinstance(voice_candidate_raw, str)
            else voice_candidate_raw
        )
        if voice_candidate:
            voice_option = (
                db.query(ServiceOption)
                .filter(
                    ServiceOption.service_name == voice_service,
                    ServiceOption.option_type == "voice_id",
                    or_(
                        ServiceOption.option_key == voice_candidate,
                        ServiceOption.option_value == voice_candidate,
                    ),
                )
                .first()
            )
            if voice_option:
                task.selected_voice_id = voice_option.option_value
                task.selected_voice_name = voice_option.option_name or voice_option.option_value
                task_config["audio_voice_id"] = voice_option.option_key
                task_config["audio_voice_name"] = voice_option.option_name or voice_option.option_key
                task_config["audio_voice_value"] = voice_option.option_value
                task_config["audio_voice_service"] = voice_service
            else:
                task.selected_voice_id = voice_candidate
                task.selected_voice_name = None
                task_config["audio_voice_id"] = voice_candidate
                task_config["audio_voice_name"] = voice_candidate
                task_config["audio_voice_value"] = voice_candidate
                task_config.setdefault("audio_voice_service", voice_service)
        else:
            task.selected_voice_id = None
            task.selected_voice_name = None
            task_config.pop("audio_voice_id", None)
            task_config.pop("audio_voice_name", None)
            task_config.pop("audio_voice_value", None)
            task_config.pop("audio_voice_service", None)
        config_changed = True

    provider_map = ensure_provider_map(task_config.get("providers"))
    task_provider_map = ensure_provider_map(task.providers)
    for key, value in task_provider_map.items():
        provider_map.setdefault(key, value)

    if "providers" in fields_set and payload.providers is not None:
        for key, value in payload.providers.items():
            if value is None or (isinstance(value, str) and not value.strip()):
                provider_map.pop(str(key), None)
            else:
                provider_map[str(key)] = str(value)
        config_changed = True

    if "media_tool" in fields_set:
        tool_value = (payload.media_tool or "").strip().lower()
        for feature in ("scene_merge", "media_compose", "finalize"):
            if tool_value:
                provider_map[feature] = tool_value
            else:
                provider_map.pop(feature, None)
        config_changed = True

    if "provider" in fields_set and (payload.provider is None or not str(payload.provider).strip()):
        provider_map.pop("video", None)

    if provider_map:
        task_config["providers"] = provider_map
        task.providers = provider_map
        config_changed = True
    else:
        task_config.pop("providers", None)
        task.providers = None
        config_changed = True

    if "subtitle_style_id" in fields_set:
        style_id_value = payload.subtitle_style_id
        if style_id_value is None:
            task.subtitle_style_id = None
            task.subtitle_style_snapshot = None
            task_config.pop("subtitle_style_id", None)
            finalize_cfg = task_config.get("finalize")
            if isinstance(finalize_cfg, dict):
                subtitles_cfg = finalize_cfg.get("subtitles")
                if isinstance(subtitles_cfg, dict):
                    subtitles_cfg.pop("style", None)
                    subtitles_cfg.pop("style_id", None)
                    subtitles_cfg.pop("style_name", None)
            config_changed = True
        else:
            try:
                style_id_int = int(style_id_value)
            except (TypeError, ValueError):
                raise HTTPException(status_code=400, detail="字幕样式 ID 无效")

            style_obj = db.get(SubtitleStyle, style_id_int)
            if not style_obj or not style_obj.is_active:
                raise HTTPException(status_code=400, detail="字幕样式不存在或已禁用")

            snapshot = _build_subtitle_style_snapshot(style_obj)
            task.subtitle_style_id = style_obj.id
            task.subtitle_style_snapshot = snapshot
            task_config["subtitle_style_id"] = style_obj.id

            finalize_cfg = task_config.get("finalize")
            if not isinstance(finalize_cfg, dict):
                finalize_cfg = {}
                task_config["finalize"] = finalize_cfg
            subtitles_cfg = finalize_cfg.get("subtitles")
            if not isinstance(subtitles_cfg, dict):
                subtitles_cfg = {}
                finalize_cfg["subtitles"] = subtitles_cfg
            subtitles_cfg.setdefault("enabled", True)
            subtitles_cfg.setdefault("embed", True)
            subtitles_cfg["style"] = snapshot.get("style")
            subtitles_cfg["style_id"] = style_obj.id
            subtitles_cfg["style_name"] = snapshot.get("name")
            config_changed = True

    if config_changed:
        task.task_config = task_config

    db.commit()
    db.refresh(task)

    return get_task(task_id, db)


@router.post("/{task_id}/steps/{step_name}/run")
def run_step_manual(task_id: int, step_name: str, db: Session = Depends(get_db)):
    """手动触发某个步骤（仅在 manual 模式或手动触发时使用）"""
    task = db.get(Task, task_id)
    if not task or task.is_deleted:
        raise HTTPException(status_code=404, detail="任务不存在")

    ensure_task_steps(db, task_id)

    step = db.query(TaskStep).filter(TaskStep.task_id == task_id, TaskStep.step_name == step_name).first()
    if not step:
        raise HTTPException(status_code=404, detail="步骤不存在")

    mapping = {
        "storyboard": "app.tasks.storyboard_task.generate_storyboard_task",
        "generate_images": "app.tasks.image_task.generate_images_task",
        "generate_audio": "app.tasks.audio_task.generate_audio_task",
        "generate_videos": "app.tasks.video_task.generate_video_task",
        "merge_scene_media": "app.tasks.scene_merge_task.merge_scene_media_task",
        "merge_video": "app.tasks.merge_task.merge_video_task",
        "finalize_video": "app.tasks.finalize_task.finalize_video_task",
    }

    if step_name not in mapping:
        raise HTTPException(status_code=400, detail="不支持的步骤名称")

    # 将步骤状态置为排队
    step.status = 0
    step.error_msg = None
    db.commit()

    # send task and record step-level external task id (best-effort)
    result = celery_app.send_task(mapping[step_name], args=[task_id], queue="default", serializer="json")
    try:
        step.external_task_id = str(result)
        db.commit()
    except Exception:
        db.rollback()

    return {"message": f"已触发步骤 {step_name} 的执行"}


@router.get("/{task_id}", response_model=TaskDetailOut)
def get_task(task_id: int, db: Session = Depends(get_db)):
    """获取任务详情（包含步骤和分镜）"""
    task = db.get(Task, task_id)
    if not task or task.is_deleted:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 获取步骤
    steps = ensure_task_steps(db, task_id)
    
    # 获取分镜
    scenes = db.query(Scene).filter(Scene.task_id == task_id).order_by(Scene.seq.asc()).all()
    
    task_dict = _serialize_task(task)

    steps_list = []
    for s in steps:
        steps_list.append({
            "id": s.id,
            "task_id": s.task_id,
            "step_name": s.step_name,
            "seq": s.seq,
            "status": s.status,
            "progress": s.progress,
            "retry_count": s.retry_count,
            "max_retries": s.max_retries,
            "params": s.params,
            "result": s.result,
            "error_msg": s.error_msg,
            "started_at": s.started_at,
            "finished_at": s.finished_at,
        })

    scenes_list = [_serialize_scene(sc) for sc in scenes]

    subtitle_document = (
        db.query(SubtitleDocument)
        .filter(SubtitleDocument.task_id == task_id)
        .one_or_none()
    )
    subtitle_doc_payload = _serialize_subtitle_document(subtitle_document) if subtitle_document else None

    return TaskDetailOut(task=task_dict, steps=steps_list, scenes=scenes_list, subtitle_document=subtitle_doc_payload)


@router.get("/{task_id}/scenes", response_model=List[SceneOut])
def list_scenes(task_id: int, db: Session = Depends(get_db)):
    """获取任务的所有分镜"""
    scenes = db.query(Scene).filter(Scene.task_id == task_id).order_by(Scene.seq.asc()).all()
    return [_serialize_scene(sc) for sc in scenes]


@router.get("/{task_id}/steps", response_model=List[TaskStepOut])
def list_steps(task_id: int, db: Session = Depends(get_db)):
    """获取任务的所有步骤"""
    steps = ensure_task_steps(db, task_id)
    return steps


@router.post("/{task_id}/scenes/{scene_id}/retry")
def retry_scene(task_id: int, scene_id: int, step_type: str, db: Session = Depends(get_db)):
    """重试单个分镜的某个步骤
    
    Args:
        task_id: 任务ID
        scene_id: 分镜ID
        step_type: 步骤类型 (image/audio/video)
    """
    scene = db.get(Scene, scene_id)
    if not scene or scene.task_id != task_id:
        raise HTTPException(status_code=404, detail="分镜不存在")

    step_name_map = {
        "image": "generate_images",
        "audio": "generate_audio",
        "video": "generate_videos",
        "merge": "merge_scene_media",
    }
    task_mapping = {
        "image": "app.tasks.image_task.generate_images_task",
        "audio": "app.tasks.audio_task.generate_audio_task",
        "video": "app.tasks.video_task.generate_video_task",
        "merge": "app.tasks.scene_merge_task.merge_scene_media_task",
    }

    step_name = step_name_map.get(step_type)
    task_path = task_mapping.get(step_type)
    if not step_name or not task_path:
        raise HTTPException(status_code=400, detail="无效的步骤类型，支持: image/audio/video/merge")

    if step_type == "image":
        if scene.image_retry_count >= 3:
            raise HTTPException(status_code=400, detail="图片生成已达最大重试次数")
        scene.image_status = 0
        scene.image_retry_count += 1
        scene.image_url = None
        scene.image_job_id = None
        scene.video_status = 0 if scene.video_status in (1, 2, 3) else scene.video_status
        scene.raw_video_url = None
        scene.video_job_id = None
        scene.merge_status = 0
        scene.merge_video_url = None
        scene.merge_retry_count = 0
        scene.merge_job_id = None
        scene.merge_meta = None
        scene.merge_video_provider = None
    elif step_type == "audio":
        if scene.audio_retry_count >= 3:
            raise HTTPException(status_code=400, detail="音频生成已达最大重试次数")
        scene.audio_status = 0
        scene.audio_retry_count += 1
        scene.audio_url = None
        scene.audio_job_id = None
        scene.merge_status = 0
        scene.merge_video_url = None
        scene.merge_retry_count = 0
        scene.merge_job_id = None
        scene.merge_meta = None
        scene.merge_video_provider = None
    elif step_type == "video":
        if scene.video_retry_count >= 3:
            raise HTTPException(status_code=400, detail="视频生成已达最大重试次数")
        scene.video_status = 0
        scene.video_retry_count += 1
        scene.raw_video_url = None
        scene.video_job_id = None
        scene.merge_status = 0
        scene.merge_video_url = None
        scene.merge_retry_count = 0
        scene.merge_job_id = None
        scene.merge_meta = None
        scene.merge_video_provider = None
    elif step_type == "merge":
        # 手动重试不限制次数，仍然记录次数供监控
        scene.merge_status = 0
        scene.merge_retry_count = (scene.merge_retry_count or 0) + 1
        scene.merge_video_url = None
        scene.merge_job_id = None
        scene.merge_meta = None
        scene.merge_video_provider = None
    else:
        raise HTTPException(status_code=400, detail="无效的步骤类型，支持: image/audio/video/merge")

    scene.error_msg = None

    step = (
        db.query(TaskStep)
        .filter(TaskStep.task_id == task_id, TaskStep.step_name == step_name)
        .first()
    )
    if step:
        step.status = 0
        step.error_msg = None
        step.finished_at = None

    db.commit()

    celery_app.send_task(
        task_path,
        args=[task_id],
        kwargs={"scene_id": scene_id},
        queue="default",
        serializer="json",
    )

    return {"message": f"分镜 {scene_id} 的 {step_type} 步骤已重置，等待重试"}


@router.post("/{task_id}/steps/generate_videos/mark_complete")
def mark_generate_videos_complete(task_id: int, db: Session = Depends(get_db)):
    """将图生视频步骤标记为已完成（适用于手动修复场景）"""
    task = db.get(Task, task_id)
    if not task or task.is_deleted:
        raise HTTPException(status_code=404, detail="任务不存在")

    ensure_task_steps(db, task_id)

    step = (
        db.query(TaskStep)
        .filter(TaskStep.task_id == task_id, TaskStep.step_name == "generate_videos")
        .first()
    )
    if not step:
        raise HTTPException(status_code=404, detail="图生视频步骤不存在")

    scenes = (
        db.query(Scene)
        .filter(Scene.task_id == task_id)
        .order_by(Scene.seq.asc())
        .all()
    )
    if not scenes:
        raise HTTPException(status_code=400, detail="任务缺少分镜，无法标记完成")

    incomplete = [
        sc for sc in scenes
        if not sc.raw_video_url or not str(sc.raw_video_url).strip()
    ]
    if incomplete:
        ids = [f"scene#{sc.id}" for sc in incomplete[:5]]
        suffix = "..." if len(incomplete) > 5 else ""
        raise HTTPException(
            status_code=400,
            detail=f"仍有分镜未完成图生视频：{', '.join(ids)}{suffix}"
        )

    total = len(scenes)

    for scene in scenes:
        if scene.video_status != 2:
            scene.video_status = 2
        if scene.merge_status == 3 and scene.audio_status == 2 and scene.audio_url:
            scene.merge_status = 0
            scene.merge_retry_count = 0

    existing_result = step.result if isinstance(step.result, dict) else {}

    step.status = 2
    step.progress = 100
    step.error_msg = None
    step.finished_at = naive_now()
    step.result = {
        "provider": existing_result.get("provider"),
        "video_prompt_provider": existing_result.get("video_prompt_provider"),
        "completed": total,
        "queued": 0,
        "failed": 0,
    }

    db.commit()

    return {"message": "图生视频步骤已标记为完成，可继续执行后续步骤"}


@router.post("/{task_id}/steps/{step_name}/retry")
def retry_step(task_id: int, step_name: str, db: Session = Depends(get_db), force: bool = False):
    """重试任务的某个步骤
    
    Args:
        task_id: 任务ID
        step_name: 步骤名称 (storyboard/generate_images/generate_audio/generate_videos/merge_scene_media/merge_video/finalize_video)
    """
    ensure_task_steps(db, task_id)

    step = db.query(TaskStep).filter(
        TaskStep.task_id == task_id,
        TaskStep.step_name == step_name
    ).first()
    
    if not step:
        raise HTTPException(status_code=404, detail="步骤不存在")
    
    # If not forced, enforce configured max retries to prevent accidental infinite retry loops
    if not force and step.retry_count >= step.max_retries:
        raise HTTPException(status_code=400, detail=f"步骤已达最大重试次数 ({step.max_retries})")
    
    # 重置步骤状态
    step.status = 0  # 待处理
    step.progress = 0
    step.retry_count += 1
    step.error_msg = None
    step.started_at = None
    step.finished_at = None
    
    db.commit()
    
    return {"message": f"步骤 {step_name} 已重置，等待重试（第 {step.retry_count} 次）"}


@router.post("/{task_id}/steps/{step_name}/reset")
def reset_step_endpoint(task_id: int, step_name: str, db: Session = Depends(get_db)):
    """重置指定步骤为待处理状态，但不增加重试次数，也不触发执行"""

    task = db.get(Task, task_id)
    if not task or task.is_deleted:
        raise HTTPException(status_code=404, detail="任务不存在")

    ensure_task_steps(db, task_id)

    step = (
        db.query(TaskStep)
        .filter(TaskStep.task_id == task_id, TaskStep.step_name == step_name)
        .first()
    )
    if not step:
        raise HTTPException(status_code=404, detail="步骤不存在")

    if step.status == 1:
        raise HTTPException(status_code=400, detail="步骤正在执行，暂时无法重置")

    step.status = 0
    step.progress = 0
    step.error_msg = None
    step.started_at = None
    step.finished_at = None
    step.external_task_id = None
    step.result = None

    db.commit()

    return {"message": f"步骤 {step_name} 已重置为待处理"}


@router.post("/{task_id}/reset/audio-pipeline")
def reset_audio_pipeline(task_id: int, db: Session = Depends(get_db)):
    """批量重置音频生成相关步骤的产物与状态。"""

    ensure_task_steps(db, task_id)
    try:
        reset_task_audio_pipeline(db, task_id)
    except TaskResetError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "message": "音频相关步骤已重置，可重新执行 generate_audio/merge_scene_media/merge_video/finalize_video",
    "reset_at": naive_now(),
    }


@router.delete("/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    """软删除任务"""
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task.is_deleted = True
    db.commit()
    
    return {"message": "任务已删除"}


@router.get("/", response_model=List[TaskOut])
def list_tasks(
    status: Optional[int] = None,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """获取任务列表"""
    query = db.query(Task).filter(Task.is_deleted == False)
    
    if status is not None:
        query = query.filter(Task.status == status)
    
    tasks = query.order_by(Task.created_at.desc()).limit(limit).offset(offset).all()
    return [_serialize_task(task) for task in tasks]

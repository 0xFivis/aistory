"""风格预设管理 API"""
from typing import Any, Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, AliasChoices, ConfigDict
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.style_preset import StylePreset
from app.models.runninghub_workflow import RunningHubWorkflow

router = APIRouter(prefix="/api/v1/style-presets", tags=["风格预设"])


def _coerce_meta(meta: Optional[Any]) -> Optional[Dict[str, Any]]:
    if meta is None:
        return None
    if isinstance(meta, dict):
        return meta
    return None


class StylePresetBase(BaseModel):
    name: str = Field(..., max_length=128, description="风格名称")
    description: Optional[str] = Field(None, description="风格说明")
    prompt_example: Optional[str] = Field(None, description="提示词结构示例")
    trigger_words: Optional[str] = Field(None, description="提示词触发词或前缀")
    word_count_strategy: Optional[str] = Field(None, description="旁白字数策略")
    channel_identity: Optional[str] = Field(None, description="频道身份描述")
    lora_id: Optional[str] = Field(
        None,
        description="LoRA ID",
        alias="liblib_lora_id",
        validation_alias=AliasChoices("lora_id", "liblib_lora_id"),
    )
    checkpoint_id: Optional[str] = Field(
        None,
        description="主模型 Checkpoint ID",
        validation_alias=AliasChoices("checkpoint_id", "model_id", "liblib_model_id"),
    )
    image_provider: Optional[str] = Field(None, description="图片生成平台，例如 liblib、runninghub")
    video_provider: Optional[str] = Field(None, description="视频生成平台，例如 nca、runninghub")
    runninghub_image_workflow_id: Optional[int] = Field(None, description="Runninghub 图片工作流配置 ID")
    runninghub_video_workflow_id: Optional[int] = Field(None, description="Runninghub 视频工作流配置 ID")
    meta: Optional[Dict[str, Any]] = Field(None, description="额外配置元数据")
    is_active: Optional[bool] = Field(True, description="是否启用")

    model_config = ConfigDict(populate_by_name=True, protected_namespaces=())


class StylePresetCreate(StylePresetBase):
    pass


class StylePresetUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=128, description="风格名称")
    description: Optional[str] = Field(None, description="风格说明")
    prompt_example: Optional[str] = Field(None, description="提示词结构示例")
    trigger_words: Optional[str] = Field(None, description="提示词触发词或前缀")
    word_count_strategy: Optional[str] = Field(None, description="旁白字数策略")
    channel_identity: Optional[str] = Field(None, description="频道身份描述")
    lora_id: Optional[str] = Field(
        None,
        description="LoRA ID",
        alias="liblib_lora_id",
        validation_alias=AliasChoices("lora_id", "liblib_lora_id"),
    )
    checkpoint_id: Optional[str] = Field(
        None,
        description="主模型 Checkpoint ID",
        validation_alias=AliasChoices("checkpoint_id", "model_id", "liblib_model_id"),
    )
    image_provider: Optional[str] = Field(None, description="图片生成平台")
    video_provider: Optional[str] = Field(None, description="视频生成平台")
    runninghub_image_workflow_id: Optional[int] = Field(None, description="Runninghub 图片工作流配置 ID")
    runninghub_video_workflow_id: Optional[int] = Field(None, description="Runninghub 视频工作流配置 ID")
    meta: Optional[Dict[str, Any]] = Field(None, description="额外配置元数据")
    is_active: Optional[bool] = Field(None, description="是否启用")

    model_config = ConfigDict(populate_by_name=True, protected_namespaces=())


class StylePresetResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    prompt_example: Optional[str]
    trigger_words: Optional[str]
    word_count_strategy: Optional[str]
    channel_identity: Optional[str]
    lora_id: Optional[str]
    checkpoint_id: Optional[str]
    image_provider: Optional[str]
    video_provider: Optional[str]
    runninghub_image_workflow_id: Optional[int]
    runninghub_video_workflow_id: Optional[int]
    meta: Optional[Dict[str, Any]]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.get("", response_model=List[StylePresetResponse], summary="获取风格预设列表")
def list_style_presets(
    include_inactive: bool = Query(False, description="是否包含已禁用的预设"),
    db: Session = Depends(get_db),
):
    query = db.query(StylePreset)
    if not include_inactive:
        query = query.filter(StylePreset.is_active == True)  # noqa: E712
    presets = query.order_by(StylePreset.created_at.desc()).all()
    return [preset.to_dict() for preset in presets]


@router.get("/{preset_id}", response_model=StylePresetResponse, summary="获取风格预设详情")
def get_style_preset(preset_id: int, db: Session = Depends(get_db)):
    preset = db.get(StylePreset, preset_id)
    if not preset:
        raise HTTPException(status_code=404, detail="风格预设不存在")
    return preset.to_dict()


@router.post("", response_model=StylePresetResponse, summary="创建风格预设", status_code=201)
def create_style_preset(payload: StylePresetCreate, db: Session = Depends(get_db)):
    existing = db.query(StylePreset).filter(StylePreset.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="风格名称已存在")

    image_provider = payload.image_provider
    video_provider = payload.video_provider

    runninghub_image_id = payload.runninghub_image_workflow_id
    runninghub_video_id = payload.runninghub_video_workflow_id

    if image_provider != "runninghub":
        runninghub_image_id = None
    elif runninghub_image_id:
        workflow = db.get(RunningHubWorkflow, runninghub_image_id)
        if not workflow or not workflow.is_active or workflow.workflow_type != "image":
            raise HTTPException(status_code=400, detail="无效的 Runninghub 图片工作流配置")

    if video_provider != "runninghub":
        runninghub_video_id = None
    elif runninghub_video_id:
        workflow = db.get(RunningHubWorkflow, runninghub_video_id)
        if not workflow or not workflow.is_active or workflow.workflow_type != "video":
            raise HTTPException(status_code=400, detail="无效的 Runninghub 视频工作流配置")

    preset = StylePreset(
        name=payload.name,
        description=payload.description,
        prompt_example=payload.prompt_example,
        trigger_words=payload.trigger_words,
        word_count_strategy=payload.word_count_strategy,
        channel_identity=payload.channel_identity,
        lora_id=payload.lora_id,
        checkpoint_id=payload.checkpoint_id,
        image_provider=image_provider,
        video_provider=video_provider,
        runninghub_image_workflow_id=runninghub_image_id,
        runninghub_video_workflow_id=runninghub_video_id,
        meta=_coerce_meta(payload.meta),
        is_active=payload.is_active if payload.is_active is not None else True,
    )

    db.add(preset)
    db.commit()
    db.refresh(preset)
    return preset.to_dict()


@router.put("/{preset_id}", response_model=StylePresetResponse, summary="更新风格预设")
def update_style_preset(preset_id: int, payload: StylePresetUpdate, db: Session = Depends(get_db)):
    preset = db.get(StylePreset, preset_id)
    if not preset:
        raise HTTPException(status_code=404, detail="风格预设不存在")

    update_data = payload.model_dump(exclude_unset=True)
    if "name" in update_data and update_data["name"] and update_data["name"] != preset.name:
        conflict = (
            db.query(StylePreset)
            .filter(StylePreset.name == update_data["name"], StylePreset.id != preset_id)
            .first()
        )
        if conflict:
            raise HTTPException(status_code=400, detail="风格名称已存在")

    if "lora_id" in update_data and "liblib_lora_id" in update_data:
        update_data.pop("liblib_lora_id", None)
    if "checkpoint_id" in update_data and "liblib_model_id" in update_data:
        update_data.pop("liblib_model_id", None)

    if "meta" in update_data:
        update_data["meta"] = _coerce_meta(update_data.get("meta"))

    image_provider = update_data.get("image_provider", preset.image_provider)
    video_provider = update_data.get("video_provider", preset.video_provider)

    if image_provider != "runninghub":
        update_data["runninghub_image_workflow_id"] = None
    elif "runninghub_image_workflow_id" in update_data and update_data["runninghub_image_workflow_id"] is not None:
        workflow = db.get(RunningHubWorkflow, update_data["runninghub_image_workflow_id"])
        if not workflow or not workflow.is_active or workflow.workflow_type != "image":
            raise HTTPException(status_code=400, detail="无效的 Runninghub 图片工作流配置")

    if video_provider != "runninghub":
        update_data["runninghub_video_workflow_id"] = None
    elif "runninghub_video_workflow_id" in update_data and update_data["runninghub_video_workflow_id"] is not None:
        workflow = db.get(RunningHubWorkflow, update_data["runninghub_video_workflow_id"])
        if not workflow or not workflow.is_active or workflow.workflow_type != "video":
            raise HTTPException(status_code=400, detail="无效的 Runninghub 视频工作流配置")

    # Backwards compatibility: if caller used legacy field names via alias
    legacy_lora = update_data.pop("liblib_lora_id", None)
    legacy_model = update_data.pop("liblib_model_id", None)
    if legacy_lora is not None and "lora_id" not in update_data:
        update_data["lora_id"] = legacy_lora
    if legacy_model is not None and "checkpoint_id" not in update_data:
        update_data["checkpoint_id"] = legacy_model

    for key, value in update_data.items():
        setattr(preset, key, value)

    db.commit()
    db.refresh(preset)
    return preset.to_dict()


@router.delete("/{preset_id}", summary="删除风格预设")
def delete_style_preset(
    preset_id: int,
    soft_delete: bool = Query(True, description="是否软删除（标记为禁用）"),
    db: Session = Depends(get_db),
):
    preset = db.get(StylePreset, preset_id)
    if not preset:
        raise HTTPException(status_code=404, detail="风格预设不存在")

    if soft_delete:
        preset.is_active = False
        db.commit()
        return {"message": "风格预设已禁用"}

    db.delete(preset)
    db.commit()
    return {"message": "风格预设已删除"}

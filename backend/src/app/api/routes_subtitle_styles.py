"""字幕样式管理 API"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.subtitle_style import SubtitleStyle
from app.models.task import Task
from app.services.subtitle_style_service import SubtitleStyleConfig, SubtitleStyleService

router = APIRouter(prefix="/api/v1/subtitle-styles", tags=["字幕样式"])
_style_service = SubtitleStyleService()


def _strip(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = value.strip()
    return text or None


def _serialize_style(style: SubtitleStyle, usage_count: int = 0) -> Dict[str, Any]:
    base = style.to_dict()
    style_fields, script_settings, effect_settings = _style_service.split_sections(base.get("style_payload"))
    payload = base.get("style_payload") if isinstance(base.get("style_payload"), dict) else {}
    meta = payload.get("_meta") if isinstance(payload.get("_meta"), dict) else {}
    effects_meta = meta.get("effects") if isinstance(meta.get("effects"), dict) else {}
    if "AlignmentVariant" not in effect_settings and "AlignmentVariant" in effects_meta:
        effect_settings["AlignmentVariant"] = effects_meta["AlignmentVariant"]
    elif "AlignmentVariant" not in effect_settings and "AlignmentVariant" in payload:
        effect_settings["AlignmentVariant"] = payload["AlignmentVariant"]
    return {
        "id": style.id,
        "name": style.name,
        "description": style.description,
        "style_fields": style_fields,
        "script_settings": script_settings,
        "effect_settings": effect_settings,
        "style_payload": base.get("style_payload") or {},
        "sample_text": style.sample_text,
        "is_active": bool(style.is_active),
        "is_default": bool(getattr(style, "is_default", False)),
        "usage_count": usage_count,
        "created_at": base.get("created_at"),
        "updated_at": base.get("updated_at"),
    }


class SubtitleStyleBase(BaseModel):
    name: str = Field(..., max_length=128, description="字幕样式名称")
    description: Optional[str] = Field(None, description="字幕样式说明")
    style_fields: Dict[str, Any] = Field(default_factory=dict, description="ASS 样式字段配置")
    script_settings: Dict[str, Any] = Field(default_factory=dict, description="ASS 脚本级配置")
    effect_settings: Dict[str, Any] = Field(default_factory=dict, description="覆盖/特效配置")
    style_payload: Optional[Dict[str, Any]] = Field(None, description="兼容字段，整体样式 JSON")
    sample_text: Optional[str] = Field(None, description="示例文本或预览说明")
    is_active: Optional[bool] = Field(True, description="是否启用")
    is_default: Optional[bool] = Field(False, description="是否设为默认")

    model_config = ConfigDict(protected_namespaces=())


class SubtitleStyleCreate(SubtitleStyleBase):
    pass


class SubtitleStyleUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=128, description="字幕样式名称")
    description: Optional[str] = Field(None, description="字幕样式说明")
    style_fields: Optional[Dict[str, Any]] = Field(None, description="ASS 样式字段配置")
    script_settings: Optional[Dict[str, Any]] = Field(None, description="ASS 脚本级配置")
    effect_settings: Optional[Dict[str, Any]] = Field(None, description="覆盖/特效配置")
    style_payload: Optional[Dict[str, Any]] = Field(None, description="兼容字段，整体样式 JSON")
    sample_text: Optional[str] = Field(None, description="示例文本或预览说明")
    is_active: Optional[bool] = Field(None, description="是否启用")
    is_default: Optional[bool] = Field(None, description="是否设为默认")

    model_config = ConfigDict(protected_namespaces=())


class SubtitleStyleResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    style_fields: Dict[str, Any]
    script_settings: Dict[str, Any]
    effect_settings: Dict[str, Any]
    style_payload: Dict[str, Any]
    sample_text: Optional[str]
    is_active: bool
    is_default: bool
    usage_count: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class SubtitleStyleCloneRequest(BaseModel):
    name: Optional[str] = Field(None, max_length=128, description="新样式名称，如未提供自动生成")
    description: Optional[str] = Field(None, description="覆盖描述，可选")
    is_active: Optional[bool] = Field(True, description="是否启用复制结果")


def _ensure_unique_name(db: Session, name: str, style_id: Optional[int] = None) -> None:
    query = db.query(SubtitleStyle).filter(SubtitleStyle.name == name)
    if style_id:
        query = query.filter(SubtitleStyle.id != style_id)
    if query.first():
        raise HTTPException(status_code=400, detail="字幕样式名称已存在")


def _normalise_payload(payload: SubtitleStyleBase | SubtitleStyleUpdate, existing: Optional[SubtitleStyle] = None) -> SubtitleStyleConfig:
    raw_existing = existing.style_payload if existing and isinstance(existing.style_payload, dict) else {}
    raw_override = payload.style_payload if isinstance(payload.style_payload, dict) else {}
    merged_raw = {**raw_existing, **raw_override}
    style_fields = payload.style_fields or {}
    script_settings = payload.script_settings or {}
    effect_settings = payload.effect_settings or {}
    config = _style_service.normalise_payload(
        style_fields=style_fields,
        script_settings=script_settings,
        effect_settings=effect_settings,
        raw_payload=merged_raw,
    )
    return config


def _apply_default(db: Session, style: SubtitleStyle) -> None:
    if not style.is_default:
        return
    (
        db.query(SubtitleStyle)
        .filter(SubtitleStyle.id != style.id, SubtitleStyle.is_default == True)  # noqa: E712
        .update({SubtitleStyle.is_default: False}, synchronize_session=False)
    )
    db.commit()


def _style_usage_count(db: Session, style_id: int) -> int:
    return (
        db.query(func.count(Task.id))
        .filter(Task.subtitle_style_id == style_id)
        .scalar()
        or 0
    )


def _usage_counts_map(db: Session) -> Dict[int, int]:
    rows = (
        db.query(Task.subtitle_style_id, func.count(Task.id))
        .filter(Task.subtitle_style_id.isnot(None))
        .group_by(Task.subtitle_style_id)
        .all()
    )
    return {style_id: count for style_id, count in rows if style_id is not None}


@router.get("", response_model=List[SubtitleStyleResponse], summary="获取字幕样式列表")
def list_subtitle_styles(
    include_inactive: bool = Query(False, description="是否包含已禁用的样式"),
    keyword: Optional[str] = Query(None, description="按名称或描述模糊搜索"),
    db: Session = Depends(get_db),
):
    query = db.query(SubtitleStyle)
    if not include_inactive:
        query = query.filter(SubtitleStyle.is_active == True)  # noqa: E712
    if keyword:
        keyword_norm = f"%{keyword.strip().lower()}%"
        query = query.filter(
            or_(
                func.lower(SubtitleStyle.name).like(keyword_norm),
                func.lower(func.coalesce(SubtitleStyle.description, "")).like(keyword_norm),
            )
        )
    styles = (
        query.order_by(SubtitleStyle.is_default.desc(), SubtitleStyle.updated_at.desc()).all()
    )
    usage_map = _usage_counts_map(db)
    return [_serialize_style(style, usage_map.get(style.id, 0)) for style in styles]


@router.get("/{style_id}", response_model=SubtitleStyleResponse, summary="获取字幕样式详情")
def get_subtitle_style(style_id: int, db: Session = Depends(get_db)):
    style = db.get(SubtitleStyle, style_id)
    if not style:
        raise HTTPException(status_code=404, detail="字幕样式不存在")
    usage = _style_usage_count(db, style_id)
    return _serialize_style(style, usage)


@router.post("", response_model=SubtitleStyleResponse, status_code=201, summary="创建字幕样式")
def create_subtitle_style(payload: SubtitleStyleCreate, db: Session = Depends(get_db)):
    name = payload.name.strip()
    _ensure_unique_name(db, name)
    try:
        config = _normalise_payload(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    style = SubtitleStyle(
        name=name,
        description=_strip(payload.description),
        style_payload=config.payload,
        sample_text=_strip(payload.sample_text),
        is_active=payload.is_active if payload.is_active is not None else True,
        is_default=payload.is_default if payload.is_default is not None else False,
    )
    db.add(style)
    db.commit()
    db.refresh(style)

    if style.is_default:
        _apply_default(db, style)

    return _serialize_style(style, 0)


@router.put("/{style_id}", response_model=SubtitleStyleResponse, summary="更新字幕样式")
def update_subtitle_style(style_id: int, payload: SubtitleStyleUpdate, db: Session = Depends(get_db)):
    style = db.get(SubtitleStyle, style_id)
    if not style:
        raise HTTPException(status_code=404, detail="字幕样式不存在")

    update_data = payload.model_dump(exclude_unset=True)
    new_name = update_data.get("name")
    if new_name and new_name.strip() != style.name:
        _ensure_unique_name(db, new_name.strip(), style_id=style_id)
        style.name = new_name.strip()

    if payload.description is not None:
        style.description = _strip(payload.description)
    if payload.sample_text is not None:
        style.sample_text = _strip(payload.sample_text)

    if any(key in update_data for key in ("style_fields", "script_settings", "effect_settings", "style_payload")):
        try:
            config = _normalise_payload(payload, existing=style)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        style.style_payload = config.payload

    if payload.is_active is not None:
        style.is_active = bool(payload.is_active)
        if not style.is_active and style.is_default:
            style.is_default = False

    if payload.is_default is not None:
        style.is_default = bool(payload.is_default)

    db.commit()
    db.refresh(style)

    if style.is_default:
        _apply_default(db, style)

    usage = _style_usage_count(db, style_id)
    return _serialize_style(style, usage)


@router.post("/{style_id}/clone", response_model=SubtitleStyleResponse, status_code=201, summary="复制字幕样式")
def clone_subtitle_style(style_id: int, payload: SubtitleStyleCloneRequest | None = None, db: Session = Depends(get_db)):
    style = db.get(SubtitleStyle, style_id)
    if not style:
        raise HTTPException(status_code=404, detail="字幕样式不存在")

    payload = payload or SubtitleStyleCloneRequest()
    base_name = payload.name.strip() if payload.name else f"{style.name} 副本"
    candidate = base_name
    suffix = 1
    while db.query(SubtitleStyle).filter(SubtitleStyle.name == candidate).first():
        candidate = f"{base_name} {suffix}"
        suffix += 1

    cloned = SubtitleStyle(
        name=candidate,
        description=_strip(payload.description) if payload.description is not None else style.description,
        style_payload=style.style_payload.copy() if isinstance(style.style_payload, dict) else {},
        sample_text=style.sample_text,
        is_active=payload.is_active if payload.is_active is not None else True,
        is_default=False,
    )
    db.add(cloned)
    db.commit()
    db.refresh(cloned)
    return _serialize_style(cloned, 0)


@router.delete("/{style_id}", summary="删除字幕样式")
def delete_subtitle_style(
    style_id: int,
    soft_delete: bool = Query(True, description="是否软删除（仅禁用）"),
    db: Session = Depends(get_db),
):
    style = db.get(SubtitleStyle, style_id)
    if not style:
        raise HTTPException(status_code=404, detail="字幕样式不存在")

    usage = _style_usage_count(db, style_id)
    if not soft_delete:
        if usage > 0:
            raise HTTPException(status_code=400, detail="仍有任务引用该样式，无法删除")
        if style.is_default:
            raise HTTPException(status_code=400, detail="默认样式无法直接删除，请先取消默认")
        db.delete(style)
        db.commit()
        return {"message": "字幕样式已删除"}

    style.is_active = False
    if style.is_default:
        style.is_default = False
    db.commit()
    return {"message": "字幕样式已禁用", "usage_count": usage}

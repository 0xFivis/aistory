"""Gemini 控制台提示词管理与调用 API"""
from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, ConfigDict, model_validator
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.gemini import GeminiPromptTemplate, GeminiPromptRecord
from app.services.gemini_service import GeminiService
from app.services.gemini_prompt_templates import (
    normalize_slug,
    build_file_path,
    relative_to_prompts,
    extract_parameters,
    save_template_content,
    load_template_content,
    delete_template_file,
    coerce_parameters_map,
    render_prompt,
    resolve_relative_path,
)
from app.services.exceptions import (
    APIException,
    ConfigurationException,
    ServiceException,
    TimeoutException,
    ValidationException,
)

router = APIRouter(prefix="/api/v1/gemini-console", tags=["Gemini 控制台"])


class TemplateSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    description: Optional[str]
    parameters: List[str]
    relative_path: str
    is_active: bool
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class TemplateDetailResponse(TemplateSummaryResponse):
    content: str


class TemplateCreatePayload(BaseModel):
    name: str = Field(..., max_length=128, description="模板名称")
    slug: Optional[str] = Field(None, max_length=128, description="模板标识（可选，留空自动生成）")
    description: Optional[str] = Field(None, description="模板说明")
    content: str = Field(..., min_length=1, description="模板内容")
    is_active: bool = Field(True, description="是否启用")


class TemplateUpdatePayload(BaseModel):
    name: Optional[str] = Field(None, max_length=128)
    slug: Optional[str] = Field(None, max_length=128)
    description: Optional[str] = Field(None)
    content: Optional[str] = Field(None, min_length=1)
    is_active: Optional[bool] = Field(None)


class PromptRequestPayload(BaseModel):
    template_id: Optional[int] = Field(None, description="模板 ID")
    template_slug: Optional[str] = Field(None, description="模板标识")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="模板参数填充值")
    generation_config: Optional[Dict[str, Any]] = Field(None, description="Gemini generation_config 覆盖")
    safety_settings: Optional[List[Dict[str, Any]]] = Field(None, description="Gemini safety 设置")
    timeout: Optional[int] = Field(180, ge=1, le=600, description="请求超时时长（秒）")

    @model_validator(mode="after")
    def validate_identifier(cls, values: "PromptRequestPayload") -> "PromptRequestPayload":
        if not values.template_id and not values.template_slug:
            raise ValueError("template_id 或 template_slug 必须提供一个")
        return values


class PromptRecordResponse(BaseModel):
    id: int
    template_id: int
    status: str
    latency_ms: Optional[int]
    parameters: Dict[str, Any]
    prompt: str
    response_text: Optional[str]
    error_message: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


def _template_to_summary(template: GeminiPromptTemplate) -> TemplateSummaryResponse:
    data = template.to_dict()
    return TemplateSummaryResponse(
        id=data["id"],
        name=data["name"],
        slug=data["slug"],
        description=data.get("description"),
        parameters=list(data.get("parameters") or []),
        relative_path=data.get("file_path"),
        is_active=bool(data.get("is_active", True)),
        created_at=data.get("created_at"),
        updated_at=data.get("updated_at"),
    )


def _template_to_detail(template: GeminiPromptTemplate, content: str) -> TemplateDetailResponse:
    summary = _template_to_summary(template)
    return TemplateDetailResponse(
        **summary.model_dump(),
        content=content,
    )


def _record_to_response(record: GeminiPromptRecord) -> PromptRecordResponse:
    data = record.to_dict()
    return PromptRecordResponse(
        id=data["id"],
        template_id=data["template_id"],
        status=data.get("status", "success"),
        latency_ms=data.get("latency_ms"),
        parameters=data.get("parameters") or {},
        prompt=data.get("prompt", ""),
        response_text=data.get("response_text"),
        error_message=data.get("error_message"),
        created_at=data.get("created_at"),
        updated_at=data.get("updated_at"),
    )


def _ensure_template_slug(db: Session, slug: str, current_id: Optional[int] = None) -> None:
    query = db.query(GeminiPromptTemplate.id).filter(GeminiPromptTemplate.slug == slug)
    if current_id:
        query = query.filter(GeminiPromptTemplate.id != current_id)
    if query.first() is not None:
        raise HTTPException(status_code=400, detail="模板标识已存在")


def _map_service_error(exc: ServiceException) -> HTTPException:
    if isinstance(exc, ValidationException):
        status_code = 422
    elif isinstance(exc, ConfigurationException):
        status_code = 500
    elif isinstance(exc, TimeoutException):
        status_code = 504
    elif isinstance(exc, APIException):
        status_code = exc.status_code or 502
    else:
        status_code = 500

    detail = {
        "message": exc.message,
        "code": exc.code,
        "details": exc.details,
    }
    return HTTPException(status_code=status_code, detail=detail)


def _load_template_or_500(template: GeminiPromptTemplate) -> str:
    try:
        return load_template_content(resolve_relative_path(template.file_path))
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=500, detail="模板文件不存在或已被删除") from exc


@router.get("/templates", response_model=List[TemplateSummaryResponse], summary="获取 Gemini 模板列表")
def list_templates(
    include_inactive: bool = Query(False, description="是否包含已禁用模板"),
    db: Session = Depends(get_db),
):
    query = db.query(GeminiPromptTemplate)
    if not include_inactive:
        query = query.filter(GeminiPromptTemplate.is_active == True)  # noqa: E712
    templates = query.order_by(GeminiPromptTemplate.created_at.desc()).all()
    return [_template_to_summary(t) for t in templates]


@router.post("/templates", response_model=TemplateDetailResponse, status_code=201, summary="创建 Gemini 模板")
def create_template(payload: TemplateCreatePayload, db: Session = Depends(get_db)):
    try:
        slug = normalize_slug(payload.slug or payload.name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _ensure_template_slug(db, slug)

    file_path = build_file_path(slug)
    relative_path = relative_to_prompts(file_path)

    if file_path.exists():
        raise HTTPException(status_code=400, detail="同名模板文件已存在")

    save_template_content(file_path, payload.content)
    parameters = extract_parameters(payload.content)

    template = GeminiPromptTemplate(
        name=payload.name,
        slug=slug,
        description=payload.description,
        file_path=relative_path,
        parameters=parameters,
        is_active=payload.is_active,
    )

    db.add(template)
    db.commit()
    db.refresh(template)

    return _template_to_detail(template, payload.content)


@router.get("/templates/{template_id}", response_model=TemplateDetailResponse, summary="获取模板详情")
def get_template(template_id: int, db: Session = Depends(get_db)):
    template = db.get(GeminiPromptTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    content = _load_template_or_500(template)
    return _template_to_detail(template, content)


@router.put("/templates/{template_id}", response_model=TemplateDetailResponse, summary="更新模板")
def update_template(template_id: int, payload: TemplateUpdatePayload, db: Session = Depends(get_db)):
    template = db.get(GeminiPromptTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    update_data = payload.model_dump(exclude_unset=True)

    new_slug = template.slug
    if "slug" in update_data and update_data["slug"]:
        try:
            candidate_slug = normalize_slug(update_data["slug"])
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if candidate_slug != template.slug:
            _ensure_template_slug(db, candidate_slug, current_id=template.id)
            new_slug = candidate_slug
    elif "slug" in update_data and not update_data["slug"]:
        # 如果传空字符串，忽略更新
        update_data.pop("slug")

    try:
        current_path = resolve_relative_path(template.file_path)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    new_path = current_path

    if new_slug != template.slug:
        new_path = build_file_path(new_slug)
        if new_path.exists() and new_path != current_path:
            raise HTTPException(status_code=400, detail="同名模板文件已存在")

    parameters = list(template.parameters or [])
    content = update_data.get("content")

    if content is not None:
        save_template_content(new_path, content)
        parameters = extract_parameters(content)
        if new_path != current_path:
            delete_template_file(current_path)
    else:
        if new_path != current_path:
            new_path.parent.mkdir(parents=True, exist_ok=True)
            if not current_path.exists():
                raise HTTPException(status_code=500, detail="模板文件不存在或已被删除")
            current_path.replace(new_path)
        try:
            content = load_template_content(new_path)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=500, detail="模板文件不存在或已被删除") from exc
        parameters = extract_parameters(content)

    if "name" in update_data and update_data["name"] is not None:
        template.name = update_data["name"]
    if "description" in update_data:
        template.description = update_data.get("description")
    if "is_active" in update_data and update_data["is_active"] is not None:
        template.is_active = bool(update_data["is_active"])

    template.slug = new_slug
    template.file_path = relative_to_prompts(new_path)
    template.parameters = parameters

    db.commit()
    db.refresh(template)

    return _template_to_detail(template, content)


@router.delete("/templates/{template_id}", summary="删除模板")
def delete_template(template_id: int, db: Session = Depends(get_db)):
    template = db.get(GeminiPromptTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    try:
        path = resolve_relative_path(template.file_path)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    delete_template_file(path)

    db.delete(template)
    db.commit()

    return {"message": "模板已删除"}


@router.post("/requests", response_model=PromptRecordResponse, summary="执行 Gemini 模板调用")
def execute_prompt(payload: PromptRequestPayload, db: Session = Depends(get_db)):
    if payload.template_id:
        template = db.get(GeminiPromptTemplate, payload.template_id)
    else:
        try:
            normalized_slug = normalize_slug(payload.template_slug or "")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        template = (
            db.query(GeminiPromptTemplate)
            .filter(GeminiPromptTemplate.slug == normalized_slug)
            .first()
        )

    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    content = _load_template_or_500(template)
    parameters = coerce_parameters_map(template.parameters or [], payload.parameters)
    prompt = render_prompt(content, parameters)

    service = GeminiService()
    timeout_seconds = payload.timeout or 180

    start_time = time.perf_counter()
    try:
        response_text = service.generate_prompt_text(
            prompt,
            generation_config=payload.generation_config,
            safety_settings=payload.safety_settings,
            timeout_seconds=timeout_seconds,
        )
        status = "success"
        error_message = None
    except ServiceException as exc:
        response_text = None
        status = "error"
        error_message = exc.message
        record = GeminiPromptRecord(
            template_id=template.id,
            prompt=prompt,
            parameters=parameters,
            response_text=None,
            error_message=error_message,
            status=status,
            latency_ms=int((time.perf_counter() - start_time) * 1000),
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        raise _map_service_error(exc)

    latency_ms = int((time.perf_counter() - start_time) * 1000)

    record = GeminiPromptRecord(
        template_id=template.id,
        prompt=prompt,
        parameters=parameters,
        response_text=response_text,
        error_message=None,
        status=status,
        latency_ms=latency_ms,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return _record_to_response(record)


@router.get("/records", response_model=List[PromptRecordResponse], summary="获取调用记录")
def list_records(
    template_id: Optional[int] = Query(None, description="按模板过滤"),
    limit: int = Query(50, ge=1, le=200, description="返回条数"),
    db: Session = Depends(get_db),
):
    query = db.query(GeminiPromptRecord).order_by(GeminiPromptRecord.created_at.desc())
    if template_id:
        query = query.filter(GeminiPromptRecord.template_id == template_id)
    records = query.limit(limit).all()
    return [_record_to_response(r) for r in records]


@router.get("/records/{record_id}", response_model=PromptRecordResponse, summary="获取单条调用记录")
def get_record(record_id: int, db: Session = Depends(get_db)):
    record = db.get(GeminiPromptRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    return _record_to_response(record)

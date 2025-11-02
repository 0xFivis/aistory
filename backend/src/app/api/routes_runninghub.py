"""Runninghub workflow configuration management API"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.runninghub_workflow import RunningHubWorkflow

router = APIRouter(prefix="/api/v1/runninghub/workflows", tags=["RunningHub"])


def _validate_workflow_type(value: str) -> str:
    normalized = (value or "").strip().lower()
    if normalized not in {"image", "video"}:
        raise HTTPException(status_code=400, detail="workflow_type 仅支持 image 或 video")
    return normalized


def _ensure_default_unique(db: Session, workflow_type: str, exclude_id: Optional[int]) -> None:
    query = db.query(RunningHubWorkflow).filter(
        RunningHubWorkflow.workflow_type == workflow_type,
        RunningHubWorkflow.is_default == True,  # noqa: E712
    )
    if exclude_id is not None:
        query = query.filter(RunningHubWorkflow.id != exclude_id)
    query.update({RunningHubWorkflow.is_default: False}, synchronize_session=False)


class RunningHubWorkflowBase(BaseModel):
    name: str = Field(..., max_length=128, description="配置名称")
    slug: Optional[str] = Field(None, max_length=64, description="唯一标识，用于代码引用")
    workflow_type: str = Field(..., description="image 或 video")
    workflow_id: str = Field(..., max_length=64, description="Runninghub workflowId")
    instance_type: Optional[str] = Field("plus", max_length=32, description="运行实例规格")
    node_info_template: Optional[List[Dict[str, Any]]] = Field(
        None, description="节点模板配置，列表结构"
    )
    defaults: Optional[Dict[str, Any]] = Field(None, description="默认参数配置")
    description: Optional[str] = Field(None, description="备注说明")
    is_active: Optional[bool] = Field(True, description="是否启用")
    is_default: Optional[bool] = Field(False, description="是否作为默认配置")

    model_config = ConfigDict(populate_by_name=True, protected_namespaces=())


class RunningHubWorkflowCreate(RunningHubWorkflowBase):
    pass


class RunningHubWorkflowUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=128)
    slug: Optional[str] = Field(None, max_length=64)
    workflow_type: Optional[str] = Field(None)
    workflow_id: Optional[str] = Field(None, max_length=64)
    instance_type: Optional[str] = Field(None, max_length=32)
    node_info_template: Optional[List[Dict[str, Any]]] = None
    defaults: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None

    model_config = ConfigDict(populate_by_name=True, protected_namespaces=())


class RunningHubWorkflowResponse(BaseModel):
    id: int
    name: str
    slug: Optional[str]
    workflow_type: str
    workflow_id: str
    instance_type: str
    node_info_template: Optional[List[Dict[str, Any]]]
    defaults: Optional[Dict[str, Any]]
    description: Optional[str]
    is_active: bool
    is_default: bool
    created_at: Optional[Any]
    updated_at: Optional[Any]

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


@router.get("", response_model=List[RunningHubWorkflowResponse], summary="列出 Runninghub 工作流配置")
def list_workflows(
    workflow_type: Optional[str] = Query(None, description="过滤 workflow 类型：image 或 video"),
    include_inactive: bool = Query(False, description="是否包含未启用配置"),
    db: Session = Depends(get_db),
):
    query = db.query(RunningHubWorkflow)
    if workflow_type:
        query = query.filter(RunningHubWorkflow.workflow_type == _validate_workflow_type(workflow_type))
    if not include_inactive:
        query = query.filter(RunningHubWorkflow.is_active == True)  # noqa: E712
    items = (
        query.order_by(
            RunningHubWorkflow.workflow_type.asc(),
            RunningHubWorkflow.is_default.desc(),
            RunningHubWorkflow.updated_at.desc(),
        )
        .all()
    )
    return items


@router.get("/{workflow_id}", response_model=RunningHubWorkflowResponse, summary="获取配置详情")
def get_workflow(workflow_id: int, db: Session = Depends(get_db)):
    record = db.get(RunningHubWorkflow, workflow_id)
    if not record:
        raise HTTPException(status_code=404, detail="配置不存在")
    return record


@router.post("", response_model=RunningHubWorkflowResponse, summary="创建配置", status_code=201)
def create_workflow(payload: RunningHubWorkflowCreate, db: Session = Depends(get_db)):
    workflow_type = _validate_workflow_type(payload.workflow_type)

    if payload.slug:
        existing_slug = (
            db.query(RunningHubWorkflow)
            .filter(RunningHubWorkflow.slug == payload.slug.strip())
            .first()
        )
        if existing_slug:
            raise HTTPException(status_code=400, detail="slug 已存在")

    if payload.is_default:
        _ensure_default_unique(db, workflow_type, exclude_id=None)

    record = RunningHubWorkflow(
        name=payload.name.strip(),
        slug=payload.slug.strip() if payload.slug else None,
        workflow_type=workflow_type,
        workflow_id=payload.workflow_id.strip(),
        instance_type=(payload.instance_type or "plus").strip(),
        node_info_template=RunningHubWorkflow.normalize_template(payload.node_info_template),
        defaults=RunningHubWorkflow.normalize_defaults(payload.defaults),
        description=payload.description.strip() if payload.description else None,
        is_active=payload.is_active if payload.is_active is not None else True,
        is_default=payload.is_default if payload.is_default is not None else False,
    )

    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.put("/{workflow_id}", response_model=RunningHubWorkflowResponse, summary="更新配置")
def update_workflow(workflow_id: int, payload: RunningHubWorkflowUpdate, db: Session = Depends(get_db)):
    record = db.get(RunningHubWorkflow, workflow_id)
    if not record:
        raise HTTPException(status_code=404, detail="配置不存在")

    data = payload.model_dump(exclude_unset=True)

    if "workflow_type" in data and data["workflow_type"] is not None:
        data["workflow_type"] = _validate_workflow_type(data["workflow_type"])

    if "slug" in data and data["slug"]:
        slug_value = data["slug"].strip()
        conflict = (
            db.query(RunningHubWorkflow)
            .filter(RunningHubWorkflow.slug == slug_value, RunningHubWorkflow.id != workflow_id)
            .first()
        )
        if conflict:
            raise HTTPException(status_code=400, detail="slug 已存在")
        data["slug"] = slug_value

    if "name" in data and data["name"]:
        data["name"] = data["name"].strip()

    if "workflow_id" in data and data["workflow_id"]:
        data["workflow_id"] = data["workflow_id"].strip()

    if "instance_type" in data and data["instance_type"]:
        data["instance_type"] = data["instance_type"].strip()

    if "description" in data and data["description"]:
        data["description"] = data["description"].strip()

    if "node_info_template" in data:
        data["node_info_template"] = RunningHubWorkflow.normalize_template(data.get("node_info_template"))

    if "defaults" in data:
        data["defaults"] = RunningHubWorkflow.normalize_defaults(data.get("defaults"))

    workflow_type = data.get("workflow_type", record.workflow_type)
    if data.get("is_default"):
        _ensure_default_unique(db, workflow_type, exclude_id=record.id)

    for key, value in data.items():
        setattr(record, key, value)

    db.commit()
    db.refresh(record)
    return record


@router.delete("/{workflow_id}", summary="删除配置")
def delete_workflow(workflow_id: int, hard_delete: bool = Query(False, description="是否物理删除"), db: Session = Depends(get_db)):
    record = db.get(RunningHubWorkflow, workflow_id)
    if not record:
        raise HTTPException(status_code=404, detail="配置不存在")

    if hard_delete:
        db.delete(record)
    else:
        record.is_active = False
        record.is_default = False
    db.commit()
    return {"message": "ok"}

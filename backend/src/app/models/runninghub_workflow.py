"""Runninghub workflow configuration model."""
from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy import Column, String, Text, Boolean, JSON, Index, UniqueConstraint

from .base import BaseModel


class RunningHubWorkflow(BaseModel):
    __tablename__ = "runninghub_workflows"

    name = Column(String(128), nullable=False, comment="展示名称")
    slug = Column(String(64), nullable=True, unique=True, comment="唯一标识，例如 image.default")
    workflow_type = Column(String(32), nullable=False, comment="workflow 类型：image 或 video")
    workflow_id = Column(String(64), nullable=False, comment="Runninghub 平台 workflowId")
    instance_type = Column(String(32), nullable=False, default="plus", comment="实例规格")
    node_info_template = Column(JSON, nullable=True, comment="节点模板配置（列表）")
    defaults = Column(JSON, nullable=True, comment="默认参数（字典）")
    description = Column(Text, nullable=True, comment="备注说明")
    is_active = Column(Boolean, nullable=False, default=True, comment="是否启用")
    is_default = Column(Boolean, nullable=False, default=False, comment="是否作为默认配置")

    __table_args__ = (
        Index("idx_runninghub_workflow_type", "workflow_type", "is_active"),
        UniqueConstraint("workflow_type", "name", name="uq_runninghub_workflow_name"),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "workflow_type": self.workflow_type,
            "workflow_id": self.workflow_id,
            "instance_type": self.instance_type,
            "node_info_template": self.node_info_template,
            "defaults": self.defaults,
            "description": self.description,
            "is_active": self.is_active,
            "is_default": self.is_default,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @staticmethod
    def normalize_template(value: Optional[Any]) -> Optional[Any]:
        if value is None:
            return None
        if isinstance(value, list):
            return value
        return None

    @staticmethod
    def normalize_defaults(value: Optional[Any]) -> Optional[Dict[str, Any]]:
        if value is None:
            return None
        if isinstance(value, dict):
            return value
        return None


__all__ = ["RunningHubWorkflow"]

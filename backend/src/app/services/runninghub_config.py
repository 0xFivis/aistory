"""Runninghub workflow configuration loading and defaults."""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.database import get_db_session
from app.models.runninghub_workflow import RunningHubWorkflow
from .exceptions import ConfigurationException


@dataclass
class RunningHubWorkflowConfig:
    """Declarative configuration for a Runninghub workflow."""

    key: str
    workflow_id: str
    instance_type: str = "plus"
    node_info_template: List[Dict[str, Any]] = field(default_factory=list)
    defaults: Dict[str, Any] = field(default_factory=dict)

    def resolve_default(self, name: str, fallback: Any) -> Any:
        value = self.defaults.get(name)
        return fallback if value is None else value

    def render_node_info(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        rendered: List[Dict[str, Any]] = []
        for entry in self.node_info_template:
            item = {}
            for key, value in entry.items():
                item[key] = self._render_value(value, context)
            rendered.append(item)
        return rendered

    @staticmethod
    def _render_value(value: Any, context: Dict[str, Any]) -> Any:
        if isinstance(value, str) and value.startswith("{{") and value.endswith("}}"):
            context_key = value[2:-2].strip()
            return context.get(context_key)
        if isinstance(value, list):
            return [RunningHubWorkflowConfig._render_value(val, context) for val in value]
        if isinstance(value, dict):
            return {
                key: RunningHubWorkflowConfig._render_value(val, context)
                for key, val in value.items()
            }
        return value


DEFAULT_IMAGE_WORKFLOW_CONFIG = RunningHubWorkflowConfig(
    key="image.default",
    workflow_id="1978319996189302785",
    instance_type="plus",
    node_info_template=[
        {"nodeId": "6", "fieldName": "text", "fieldValue": "{{prompt}}"},
        {"nodeId": "5", "fieldName": "width", "fieldValue": "{{width}}"},
        {"nodeId": "5", "fieldName": "height", "fieldValue": "{{height}}"},
    ],
    defaults={
        "width": 864,
        "height": 1536,
        "poll_attempts": 6,
        "poll_interval": 60.0,
        "initial_delay": 60.0,
        "busy_wait": 10.0,
        "create_attempts": 3,
    },
)

DEFAULT_VIDEO_WORKFLOW_CONFIG = RunningHubWorkflowConfig(
    key="video.default",
    workflow_id="1950150331004010497",
    instance_type="plus",
    node_info_template=[
        {"nodeId": "113", "fieldName": "select", "fieldValue": "{{node_113}}"},
        {"nodeId": "153", "fieldName": "select", "fieldValue": "{{node_153}}"},
        {"nodeId": "247", "fieldName": "select", "fieldValue": "{{node_247}}"},
        {"nodeId": "272", "fieldName": "index", "fieldValue": "{{node_272}}"},
        {"nodeId": "107", "fieldName": "value", "fieldValue": "{{duration}}"},
        {"nodeId": "135", "fieldName": "image", "fieldValue": "{{image_url}}"},
        {"nodeId": "116", "fieldName": "text", "fieldValue": "{{prompt}}"},
    ],
    defaults={
        "node_113": 2,
        "node_153": 2,
        "node_247": 4,
        "node_272": 2,
        "poll_attempts": 6,
        "poll_interval": 60.0,
        "initial_delay": 60.0,
        "busy_wait": 10.0,
        "create_attempts": 3,
        "min_duration": 2,
        "max_duration": 8,
    },
)

_CONFIG_FALLBACKS = {
    DEFAULT_IMAGE_WORKFLOW_CONFIG.key: DEFAULT_IMAGE_WORKFLOW_CONFIG,
    DEFAULT_VIDEO_WORKFLOW_CONFIG.key: DEFAULT_VIDEO_WORKFLOW_CONFIG,
}


def _fallback_for_type(workflow_type: Optional[str]) -> Optional[RunningHubWorkflowConfig]:
    if workflow_type == "image":
        return DEFAULT_IMAGE_WORKFLOW_CONFIG
    if workflow_type == "video":
        return DEFAULT_VIDEO_WORKFLOW_CONFIG
    return None


def get_runninghub_config(
    key: Optional[str] = None,
    *,
    config_id: Optional[int] = None,
    workflow_type: Optional[str] = None,
    db: Optional[Session] = None,
    fallback: Optional[RunningHubWorkflowConfig] = None,
) -> RunningHubWorkflowConfig:
    if key is None and config_id is None and workflow_type is None:
        raise ConfigurationException("缺少 Runninghub 配置查找参数", service_name="Runninghub")

    base_fallback = fallback or (key and _CONFIG_FALLBACKS.get(key)) or _fallback_for_type(workflow_type)

    session = db or get_db_session()
    should_close = db is None
    try:
        query = session.query(RunningHubWorkflow).filter(RunningHubWorkflow.is_active == True)  # noqa: E712

        if config_id is not None:
            try:
                config_id = int(config_id)
            except (TypeError, ValueError):
                config_id = None
            if config_id:
                query = query.filter(RunningHubWorkflow.id == config_id)
            else:
                query = query.filter(sa.false())  # type: ignore[name-defined]
        elif key:
            query = query.filter(RunningHubWorkflow.slug == key)
        elif workflow_type:
            query = (
                query.filter(RunningHubWorkflow.workflow_type == workflow_type)
                .order_by(RunningHubWorkflow.is_default.desc(), RunningHubWorkflow.updated_at.desc())
            )

        record = query.first()

        if not record:
            if base_fallback is None:
                identifier = key or config_id or workflow_type or "unknown"
                raise ConfigurationException(
                    f"Runninghub workflow config '{identifier}' not found",
                    service_name="Runninghub",
                )
            return base_fallback

        resolved_fallback = base_fallback or _fallback_for_type(record.workflow_type)
        return _config_from_record(record, resolved_fallback)
    finally:
        if should_close:
            try:
                session.close()
            except Exception:  # pragma: no cover - defensive close
                pass


def _config_from_record(
    record: RunningHubWorkflow,
    fallback: Optional[RunningHubWorkflowConfig],
) -> RunningHubWorkflowConfig:
    defaults: Dict[str, Any] = {}
    if fallback:
        defaults.update(copy.deepcopy(fallback.defaults))

    if isinstance(record.defaults, dict):
        defaults.update(copy.deepcopy(record.defaults))

    instance_type = record.instance_type or (fallback.instance_type if fallback else "plus")

    if not record.workflow_id and not (fallback and fallback.workflow_id):
        raise ConfigurationException("Runninghub workflow 缺少 workflow_id", service_name="Runninghub")

    workflow_id = record.workflow_id or fallback.workflow_id

    template = record.node_info_template
    if not isinstance(template, list):
        template = copy.deepcopy(fallback.node_info_template) if fallback else []
    else:
        template = copy.deepcopy(template)

    key = record.slug or (fallback.key if fallback else f"{record.workflow_type}.{record.id}")

    return RunningHubWorkflowConfig(
        key=key,
        workflow_id=str(workflow_id),
        instance_type=str(instance_type),
        node_info_template=template,
        defaults=defaults,
    )


__all__ = [
    "RunningHubWorkflowConfig",
    "DEFAULT_IMAGE_WORKFLOW_CONFIG",
    "DEFAULT_VIDEO_WORKFLOW_CONFIG",
    "get_runninghub_config",
]

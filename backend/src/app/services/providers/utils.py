"""Utility helpers for provider selection logic."""
from __future__ import annotations

from typing import Dict

from app.models.task import Task


def collect_provider_candidates(task: Task) -> Dict[str, str]:
    """Merge provider overrides from task_config and persisted task.providers."""
    provider_map: Dict[str, str] = {}
    task_config = task.task_config or {}
    if isinstance(task_config, dict):
        config_map = task_config.get("providers") if isinstance(task_config.get("providers"), dict) else {}
        provider_map.update({k: str(v) for k, v in config_map.items() if isinstance(v, str) or isinstance(v, (int, float))})
    if isinstance(task.providers, dict):
        provider_map.update({k: str(v) for k, v in task.providers.items() if isinstance(v, str) or isinstance(v, (int, float))})
    return provider_map


__all__ = ["collect_provider_candidates"]

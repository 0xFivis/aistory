"""Shared helpers for Celery task modules."""
from __future__ import annotations

from typing import Any, Dict

from .interrupts import (  # re-export for convenience
	StepInterruptController,
	mark_scene_interrupted,
	refresh_step,
	reset_interrupted_scenes,
	summarize_status_counts,
)


def ensure_provider_map(raw: Any) -> Dict[str, str]:
	"""Return a shallow copy of provider mappings if dict-like, else empty."""
	if isinstance(raw, dict):
		return {str(key): str(value) for key, value in raw.items() if value is not None}
	return {}


__all__ = [
	"ensure_provider_map",
	"StepInterruptController",
	"mark_scene_interrupted",
	"refresh_step",
	"reset_interrupted_scenes",
	"summarize_status_counts",
]

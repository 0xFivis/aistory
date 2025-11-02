"""Helpers for importing storyboard scripts into scenes."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.media import Scene
from app.models.task import Task, TaskStep
from app.tasks.utils import ensure_provider_map
from app.utils.timezone import naive_now


@dataclass
class ScriptPersistResult:
    scene_count: int
    created: bool


def persist_script_scenes(
    db: Session,
    *,
    task: Task,
    step: TaskStep,
    script_items: List[Dict[str, Any]],
    provider_label: str = "script_import",
    allow_existing: bool = False,
    trigger_words: Optional[str] = None,
) -> ScriptPersistResult:
    """Create storyboard scenes from a pre-parsed script payload."""
    if not isinstance(script_items, list) or not script_items:
        raise ValueError("storyboard_script 为空")

    cleaned_trigger = _clean_text(trigger_words)

    existing_scenes = (
        db.query(Scene)
        .filter(Scene.task_id == task.id)
        .order_by(Scene.seq.asc())
        .all()
    )

    if existing_scenes:
        if not allow_existing:
            raise ValueError("任务已有分镜，禁止覆盖")
        _ensure_existing_scene_prompts(existing_scenes, cleaned_trigger)
        scene_count = len(existing_scenes)
        _apply_step_metadata(step, provider_label, scene_count)
        _apply_task_metadata(task, provider_label, scene_count)
        return ScriptPersistResult(scene_count=scene_count, created=False)

    for idx, item in enumerate(script_items, start=1):
        seq = int(item.get("scene_number") or idx)
        title = _clean_text(item.get("title"))
        visual_raw = _clean_text(item.get("visual"))
        animation = _clean_text(item.get("animation"))
        narration = _clean_text(item.get("narration"))
        dialogue = _clean_text(item.get("dialogue"))

        visual_prompt = _apply_trigger_words(visual_raw, cleaned_trigger)
        video_prompt = animation

        params: Dict[str, Any] = {
            "source": "script",
            "title": title,
            "image_prompt": visual_prompt,
            "image_prompt_raw": visual_raw,
            "animation": animation,
            "narration": narration,
            "dialogue": dialogue,
            "video_prompt": video_prompt,
        }

        extras = item.get("extras")
        if extras:
            params["extras"] = extras
        raw_payload = item.get("raw")
        if raw_payload:
            params["raw"] = raw_payload

        scene = Scene(
            task_id=task.id,
            seq=seq,
            status=0,
            narration_text=narration,
            narration_word_count=len(narration) if narration else None,
            image_prompt=visual_prompt,
            video_prompt=video_prompt,
            image_status=0,
            audio_status=0,
            video_status=0,
            image_retry_count=0,
            audio_retry_count=0,
            video_retry_count=0,
            params=params,
        )
        db.add(scene)

    scene_count = len(script_items)
    _apply_step_metadata(step, provider_label, scene_count)
    _apply_task_metadata(task, provider_label, scene_count)
    return ScriptPersistResult(scene_count=scene_count, created=True)


def _ensure_existing_scene_prompts(scenes: List[Scene], trigger_words: Optional[str]) -> None:
    if not trigger_words:
        return

    for scene in scenes:
        params = scene.params if isinstance(scene.params, dict) else {}
        visual_raw = _clean_text(
            params.get("image_prompt_raw")
            or params.get("image_prompt")
            or scene.image_prompt
        )
        new_prompt = _apply_trigger_words(visual_raw, trigger_words)
        if not new_prompt or new_prompt == scene.image_prompt:
            continue

        animation = _clean_text(params.get("animation"))
        scene.image_prompt = new_prompt
        scene.video_prompt = animation

        params["image_prompt"] = new_prompt
        if visual_raw:
            params["image_prompt_raw"] = visual_raw
            params.pop("visual_raw", None)
            params.pop("visual", None)
        else:
            params.pop("image_prompt_raw", None)
        if animation:
            params["animation"] = animation
            params["video_prompt"] = animation
        else:
            params.pop("video_prompt", None)
        scene.params = params


def _apply_trigger_words(visual: Optional[str], trigger_words: Optional[str]) -> Optional[str]:
    if not visual:
        return visual

    stripped_visual = visual.strip()
    if not stripped_visual:
        return None

    if not trigger_words:
        return stripped_visual

    stripped_prefix = trigger_words.strip()
    if not stripped_prefix:
        return stripped_visual

    normalized_visual = stripped_visual.lower()
    normalized_prefix = stripped_prefix.lower()
    if normalized_visual.startswith(f"{normalized_prefix},") or normalized_visual.startswith(
        f"{normalized_prefix}，"
    ):
        return stripped_visual

    return f"{stripped_prefix}, {stripped_visual}"


def _apply_step_metadata(step: TaskStep, provider_label: str, scene_count: int) -> None:
    now = naive_now()
    if step.started_at is None:
        step.started_at = now
    step.finished_at = now
    step.status = 2
    step.progress = 100
    step.provider = provider_label
    step.error_msg = None
    step.result = {
        "provider": provider_label,
        "scene_count": scene_count,
        "source": "script",
    }


def _apply_task_metadata(task: Task, provider_label: str, scene_count: int) -> None:
    providers = ensure_provider_map(task.providers)
    providers["storyboard"] = provider_label
    task.providers = providers
    task.total_scenes = scene_count
    task.completed_scenes = 0
    task.error_msg = None


def _clean_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        result = value.strip()
    else:
        result = str(value).strip()
    return result or None


__all__ = ["persist_script_scenes", "ScriptPersistResult"]

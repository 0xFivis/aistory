"""Utility functions for batch resetting task steps."""
from __future__ import annotations

from typing import Iterable

from sqlalchemy.orm import Session

from app.models.media import Scene
from app.models.task import Task, TaskStep
from app.models.subtitle_document import SubtitleDocument
from app.utils.timezone import naive_now


STEP_RESET_SEQUENCE = (
    "generate_audio",
    "merge_scene_media",
    "merge_video",
    "finalize_video",
)


class TaskResetError(RuntimeError):
    """Raised when reset preconditions fail."""


def _get_task(db: Session, task_id: int) -> Task:
    task = db.get(Task, task_id)
    if not task or task.is_deleted:
        raise TaskResetError("任务不存在或已删除")
    return task


def _ensure_steps(db: Session, task_id: int, expected: Iterable[str]) -> dict[str, TaskStep]:
    steps = (
        db.query(TaskStep)
        .filter(TaskStep.task_id == task_id, TaskStep.step_name.in_(list(expected)))
        .all()
    )
    mapping = {step.step_name: step for step in steps}
    missing = [name for name in expected if name not in mapping]
    if missing:
        raise TaskResetError(f"缺少任务步骤: {', '.join(missing)}")
    return mapping


def reset_step(step: TaskStep) -> None:
    step.status = 0
    step.progress = 0
    step.retry_count = 0
    step.error_msg = None
    step.started_at = None
    step.finished_at = None
    step.result = None


def reset_scenes_audio(scene: Scene) -> None:
    scene.audio_status = 0
    scene.audio_retry_count = 0
    scene.audio_url = None
    scene.audio_job_id = None
    scene.audio_meta = None
    scene.audio_provider = None
    scene.audio_duration = None

    scene.merge_status = 0
    scene.merge_retry_count = 0
    scene.merge_video_url = None
    scene.merge_job_id = None
    scene.merge_meta = None
    scene.merge_video_provider = None


def reset_task_compose(task: Task) -> None:
    task.merged_video_url = None
    if isinstance(task.result, dict):
        task.result.pop("merged_video", None)


def reset_task_finalize(db: Session, task: Task) -> None:
    task.final_video_url = None
    if isinstance(task.result, dict):
        task.result.pop("final_video", None)
        task.result.pop("finalize", None)
        task.result.pop("final_video_url", None)
        task.result.pop("finalize_pipeline", None)
        task.result.pop("subtitle_api_path", None)
        task.result.pop("subtitle_srt_api_path", None)
        task.result.pop("subtitle_ass_api_path", None)
        task.result.pop("subtitle_public_url", None)
        task.result.pop("subtitle_ass_public_url", None)
        task.result.pop("subtitle_document_id", None)
        task.result.pop("finalize_artifacts", None)

    document = (
        db.query(SubtitleDocument)
        .filter(SubtitleDocument.task_id == task.id)
        .one_or_none()
    )
    if document:
        db.delete(document)


def reset_task_audio_pipeline(db: Session, task_id: int) -> None:
    """Reset audio → scene merge → merge video → finalize outputs for a task."""
    task = _get_task(db, task_id)
    steps = _ensure_steps(db, task_id, STEP_RESET_SEQUENCE)

    scenes = (
        db.query(Scene)
        .filter(Scene.task_id == task_id)
        .order_by(Scene.seq.asc())
        .all()
    )

    if not scenes:
        raise TaskResetError("任务缺少分镜，无法重置")

    # Reset audio (step 3) and scene merge (step 5) scene-level data
    for scene in scenes:
        reset_scenes_audio(scene)

    # Reset step statuses sequentially
    reset_step(steps["generate_audio"])
    reset_step(steps["merge_scene_media"])

    # Reset merge video artifacts (step 6)
    reset_step(steps["merge_video"])
    reset_task_compose(task)

    # Reset finalize outputs (step 7)
    reset_step(steps["finalize_video"])
    reset_task_finalize(db, task)

    task.error_msg = None
    task.status = 0
    task.progress = 0
    task.completed_scenes = sum(
        1 for sc in scenes if sc.image_status == 2 and sc.video_status == 2
    )
    task.updated_at = naive_now()

    db.commit()

__all__ = [
    "reset_task_audio_pipeline",
    "TaskResetError",
]

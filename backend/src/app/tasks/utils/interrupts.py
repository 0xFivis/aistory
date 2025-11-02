"""Helpers for handling step-level interrupts across media tasks."""
from __future__ import annotations

from typing import Callable, Iterable, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.task import TaskStep
from app.utils.timezone import naive_now


def refresh_step(db: Session, step: TaskStep) -> TaskStep:
    """Reload the TaskStep from the DB and return it."""
    try:
        db.refresh(step)
        return step
    except Exception:
        step = (
            db.query(TaskStep)
            .filter(TaskStep.id == step.id)
            .first()
        )
        if not step:
            raise RuntimeError("步骤记录不存在或已被删除")
        return step


def reset_interrupted_scenes(
    db: Session,
    scenes: Iterable,
    *,
    status_attr: str,
    celery_id_attr: Optional[str] = None,
    job_id_attr: Optional[str] = None,
    url_attr: Optional[str] = None,
    extra_reset: Optional[Callable[[object], None]] = None,
) -> int:
    """Reset all scenes with status == 6 back to pending (0).

    Returns the number of scenes reset.
    """
    count = 0
    for scene in scenes:
        if getattr(scene, status_attr, None) == 6:
            setattr(scene, status_attr, 0)
            setattr(scene, "started_at", None)
            setattr(scene, "finished_at", None)
            setattr(scene, "error_msg", None)
            if celery_id_attr:
                setattr(scene, celery_id_attr, None)
            if job_id_attr:
                setattr(scene, job_id_attr, None)
            if url_attr:
                setattr(scene, url_attr, None)
            if extra_reset:
                extra_reset(scene)
            count += 1
    if count:
        db.commit()
    return count


def mark_scene_interrupted(scene, *, status_attr: str) -> None:
    """Mark scene as interrupted, preserving/annotating error message."""
    setattr(scene, status_attr, 6)
    setattr(scene, "finished_at", naive_now())
    message = (getattr(scene, "error_msg", "") or "").strip()
    if "[interrupted]" not in message:
        message = f"{message} [interrupted]".strip()
    setattr(scene, "error_msg", message or None)


def summarize_status_counts(scenes: Iterable, *, status_attr: str) -> Tuple[int, int, int, int]:
    """Return (completed, queued, failed, pending) counts for the given status attribute."""
    completed = queued = failed = pending = 0
    for sc in scenes:
        status = getattr(sc, status_attr, None)
        if status == 2:
            completed += 1
        elif status == 1:
            queued += 1
        elif status == 3:
            failed += 1
        elif status == 6:
            pending += 1
        else:
            pending += 1
    return completed, queued, failed, pending


class StepInterruptController:
    """Utility to coordinate reset/refresh/interrupt checks for a task step."""

    def __init__(
        self,
        *,
        db: Session,
        step: TaskStep,
        status_attr: str,
        celery_id_attr: Optional[str] = None,
        job_id_attr: Optional[str] = None,
        url_attr: Optional[str] = None,
        extra_reset: Optional[Callable[[object], None]] = None,
        interrupt_clear_attrs: Optional[Iterable[str]] = None,
        interrupt_cleanup: Optional[Callable[[object], None]] = None,
    ) -> None:
        self.db = db
        self.step = step
        self.status_attr = status_attr
        self.celery_id_attr = celery_id_attr
        self.job_id_attr = job_id_attr
        self.url_attr = url_attr
        self.extra_reset = extra_reset
        self.interrupt_clear_attrs = tuple(interrupt_clear_attrs or ())
        self.interrupt_cleanup = interrupt_cleanup

    def reset_interrupted(self, scenes: Iterable) -> int:
        """Reset any scenes marked as interrupted (status == 6) back to pending."""
        return reset_interrupted_scenes(
            self.db,
            scenes,
            status_attr=self.status_attr,
            celery_id_attr=self.celery_id_attr,
            job_id_attr=self.job_id_attr,
            url_attr=self.url_attr,
            extra_reset=self.extra_reset,
        )

    def refresh_step(self) -> TaskStep:
        """Refresh and cache the latest TaskStep state."""
        self.step = refresh_step(self.db, self.step)
        return self.step

    def should_abort(self) -> bool:
        """Return True if the step has been marked interrupted and work should halt."""
        step = self.refresh_step()
        return getattr(step, "status", None) == 6

    def handle_interrupt_after_provider(self, scene) -> bool:
        """After invoking a provider, re-check interruption and mark scene if needed."""
        if not self.should_abort():
            return False
        mark_scene_interrupted(scene, status_attr=self.status_attr)
        for attr in self.interrupt_clear_attrs:
            try:
                setattr(scene, attr, None)
            except Exception:
                pass
        if self.interrupt_cleanup:
            try:
                self.interrupt_cleanup(scene)
            except Exception:
                pass
        return True

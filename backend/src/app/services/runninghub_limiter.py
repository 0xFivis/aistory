"""Deprecated module retained for backwards compatibility.

The project now relies on :mod:`app.services.concurrency_manager` for
distributed provider throttling. Importing from this module will raise an
error to highlight the change early during execution.
"""

from __future__ import annotations


def __getattr__(name: str):  # pragma: no cover - defensive
    raise RuntimeError(
        "app.services.runninghub_limiter 已废弃，请改用 app.services.concurrency_manager"
    )


__all__ = []

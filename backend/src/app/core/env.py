"""Centralised environment loader used across the project."""
from __future__ import annotations

import os
from pathlib import Path
from typing import List

from dotenv import find_dotenv, load_dotenv

_ENV_LOADED = False


def _discover_env_files() -> List[str]:
    """Return ordered, unique .env file paths that exist on disk."""
    candidates: List[Path] = []

    explicit = os.environ.get("ENV_FILE") or os.environ.get("DOTENV_PATH")
    if explicit:
        candidates.append(Path(explicit).expanduser())

    for name in (".env", ".env.local"):
        located = find_dotenv(filename=name, raise_error_if_not_found=False)
        if located:
            candidates.append(Path(located))

    fallback = Path(__file__).resolve().parents[2] / ".env"
    candidates.append(fallback)

    seen = set()
    resolved: List[str] = []
    for path in candidates:
        try:
            canonical = path.resolve()
        except OSError:
            continue
        key = str(canonical)
        if key in seen or not canonical.is_file():
            continue
        seen.add(key)
        resolved.append(key)
    return resolved


def load_env(override: bool = False) -> bool:
    """Load environment variables from discovered .env files once per process."""
    global _ENV_LOADED
    if _ENV_LOADED and not override:
        return False

    loaded = False
    for env_path in _discover_env_files():
        load_dotenv(env_path, override=override)
        loaded = True

    _ENV_LOADED = True
    return loaded


__all__ = ["load_env"]

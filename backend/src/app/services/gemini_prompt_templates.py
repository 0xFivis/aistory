"""Utilities for managing Gemini prompt templates stored on disk."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Iterable, Mapping

PROMPTS_ROOT = Path(__file__).resolve().parent.parent / "prompts"
CONSOLE_PROMPT_DIR = PROMPTS_ROOT / "console"

_PARAM_PATTERN = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


def ensure_console_dir() -> Path:
    """Ensure the console prompts directory exists and return it."""
    CONSOLE_PROMPT_DIR.mkdir(parents=True, exist_ok=True)
    return CONSOLE_PROMPT_DIR


def normalize_slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip().lower())
    slug = re.sub(r"-+", "-", slug).strip("-_")
    if not slug:
        raise ValueError("模板标识不能为空")
    return slug


def build_file_path(slug: str) -> Path:
    base = ensure_console_dir().resolve()
    path = (base / f"{slug}.tmpl").resolve()
    if not str(path).startswith(str(base)):
        raise ValueError("非法模板路径")
    return path


def relative_to_prompts(path: Path) -> str:
    base = PROMPTS_ROOT.resolve()
    return str(path.resolve().relative_to(base))


def resolve_relative_path(relative_path: str) -> Path:
    base = PROMPTS_ROOT.resolve()
    path = (PROMPTS_ROOT / relative_path).resolve()
    console_base = ensure_console_dir().resolve()
    if not str(path).startswith(str(console_base)):
        raise ValueError("模板路径必须位于 console 目录下")
    if not str(path).startswith(str(base)):
        raise ValueError("模板路径必须位于 prompts 目录下")
    return path


def extract_parameters(content: str) -> list[str]:
    if not content:
        return []
    keys = {match.group(1) for match in _PARAM_PATTERN.finditer(content)}
    return sorted(keys)


def render_prompt(content: str, values: Mapping[str, str | None]) -> str:
    values = values or {}
    def replacer(match: re.Match[str]) -> str:
        key = match.group(1)
        value = values.get(key, "")
        if value is None:
            return ""
        return str(value)

    return _PARAM_PATTERN.sub(replacer, content)


def save_template_content(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def load_template_content(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"模板文件不存在: {path}")
    return path.read_text(encoding="utf-8")


def delete_template_file(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        return


def coerce_parameters_map(keys: Iterable[str], values: Mapping[str, object] | None) -> Dict[str, str]:
    result: Dict[str, str] = {}
    if not keys:
        return result
    provided = values or {}
    for key in keys:
        raw = provided.get(key, "")
        if raw is None:
            result[key] = ""
        else:
            result[key] = str(raw)
    return result

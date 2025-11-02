import os
import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from app.config.settings import get_settings
from app.services.subtitle_service import SubtitleService


@pytest.fixture
def subtitle_service(tmp_path, monkeypatch):
    tmp_storage = tmp_path / "storage"
    tmp_storage.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("DATABASE_URL", os.environ.get("DATABASE_URL", "sqlite:///tmp/test.db"))
    monkeypatch.setenv("STORAGE_BASE_PATH", str(tmp_storage))
    monkeypatch.setenv("STORAGE_PUBLIC_BASE_URL", "")

    get_settings.cache_clear()
    service = SubtitleService()
    yield service
    get_settings.cache_clear()


def _extract_dialogue_lines(document: str):
    return [line for line in document.splitlines() if line.startswith("Dialogue:")]


def test_sequence_mode_splits_text_without_word_data(subtitle_service):
    segments = [
        {
            "start": 0.0,
            "end": 2.4,
            "text": "You are my sunshine",
            "words": [],
        }
    ]
    style_payload = {
        "SequenceMode": "word-continuous",
        "SequenceAnchor": {"x": 540, "y": 1550},
        "SequenceJitter": {"dx": 2, "dy": 2},
        "TextOverride": "\\fad(50,50)",
    }
    render_settings = {
        "title": "Test",
        "play_res_x": 1080,
        "play_res_y": 1920,
        "wrap_style": 1,
        "scaled_border_and_shadow": True,
        "ycbcr_matrix": "TV.601",
    }

    style_fields = subtitle_service._build_style_fields("Default", style_payload)
    document = subtitle_service._render_ass(segments, style_fields, render_settings, style_payload)

    dialogue_lines = _extract_dialogue_lines(document)
    assert len(dialogue_lines) == 4
    assert all("\\move" in line for line in dialogue_lines)
    texts = [line.split("}")[-1] for line in dialogue_lines]
    assert texts == ["You", "are", "my", "sunshine"]


def test_sequence_mode_adds_anchor_when_jitter_zero(subtitle_service):
    segments = [
        {
            "start": 1.0,
            "end": 2.2,
            "text": "Always bright",
            "words": [],
        }
    ]
    style_payload = {
        "SequenceMode": "word-continuous",
        "SequenceAnchor": {"x": 540, "y": 1550},
        "SequenceJitter": {"dx": 0, "dy": 0},
    }
    render_settings = {
        "title": "Test",
        "play_res_x": 1080,
        "play_res_y": 1920,
        "wrap_style": 1,
        "scaled_border_and_shadow": True,
        "ycbcr_matrix": "TV.601",
    }

    style_fields = subtitle_service._build_style_fields("Default", style_payload)
    document = subtitle_service._render_ass(segments, style_fields, render_settings, style_payload)

    dialogue_lines = _extract_dialogue_lines(document)
    assert len(dialogue_lines) == 2
    assert all("\\pos(540,1550)" in line for line in dialogue_lines)
    assert all("\\move" not in line for line in dialogue_lines)

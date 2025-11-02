"""Seed a style preset based on the bundled n8n workflow story."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.database import get_db_session
from app.models.style_preset import StylePreset

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = ROOT.parent / "n8nstory.json"


def _load_workflow() -> Dict[str, Any]:
    with WORKFLOW_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _find_assignment(assignments: list[Dict[str, Any]], name: str) -> Optional[str]:
    for item in assignments:
        if item.get("name") == name:
            raw = item.get("value")
            if isinstance(raw, str):
                return raw
    return None


def _strip_prefix(value: Optional[str]) -> Optional[str]:
    if not value:
        return value
    return value[1:].strip() if value.startswith("=") else value.strip()


def _fix_encoding(value: Optional[str]) -> Optional[str]:
    if not value:
        return value
    replacements = {
        "â": "'",
        "â": "-",
        "â": "-",
        "â": '"',
        "â": '"',
    }
    cleaned = value
    for bad, good in replacements.items():
        cleaned = cleaned.replace(bad, good)
    return cleaned


def upsert_style_preset(db: Session) -> StylePreset:
    workflow = _load_workflow()

    style_name = "历史人物-写实风格"

    preset = db.query(StylePreset).filter(StylePreset.name == style_name).first()
    if preset:
        return preset

    style_description = "基于 n8n 模板“历史人物-写实风格-文生图图生视频”的配置整理"

    assignments = workflow["nodes"][0]["parameters"]["assignments"]["assignments"]

    prompt_example = _fix_encoding(_strip_prefix(_find_assignment(assignments, "Liblib 提示词示例")))
    trigger_words = _strip_prefix(_find_assignment(assignments, "Liblib 触发词"))

    checkpoint_id = _strip_prefix(_find_assignment(assignments, "主模型编号"))
    lora_id = _strip_prefix(_find_assignment(assignments, "Lora 编号"))

    fish_voice_id = _strip_prefix(_find_assignment(assignments, "Fish audio 音色"))
    bgm_url = _strip_prefix(_find_assignment(assignments, "配乐"))

    word_count_strategy = "Each storyboard narration line should stay between 4 and 28 Chinese characters with dynamic pacing."

    channel_identity = "历史人物"

    meta: Dict[str, Any] = {
        "n8n_workflow": workflow.get("name"),
        "runninghub": {
            "image_workflow_id": "1978319996189302785",
            "video_workflow_id": "1950150331004010497",
            "instance_type": "plus",
            "image_node_defaults": [
                {"nodeId": "6", "fieldName": "text"},
                {"nodeId": "5", "fieldName": "width", "fieldValue": 864},
                {"nodeId": "5", "fieldName": "height", "fieldValue": 1536},
            ],
            "video_node_defaults": [
                {"nodeId": "113", "fieldName": "select", "fieldValue": 2},
                {"nodeId": "153", "fieldName": "select", "fieldValue": 2},
                {"nodeId": "247", "fieldName": "select", "fieldValue": 4},
                {"nodeId": "272", "fieldName": "index", "fieldValue": 2},
                {"nodeId": "107", "fieldName": "value"},
                {"nodeId": "135", "fieldName": "image"},
                {"nodeId": "116", "fieldName": "text"},
            ],
        },
        "audio": {
            "audio_voice_id": fish_voice_id,
            "bgm_url": bgm_url,
        },
    }

    preset = StylePreset(
        name=style_name,
        description=style_description,
        prompt_example=prompt_example,
        trigger_words=trigger_words,
        word_count_strategy=word_count_strategy,
        channel_identity=channel_identity,
        lora_id=lora_id,
        checkpoint_id=checkpoint_id,
        meta=meta,
        is_active=True,
    )

    db.add(preset)
    db.commit()
    db.refresh(preset)
    return preset


def main() -> None:
    db = get_db_session()
    try:
        preset = upsert_style_preset(db)
        print(f"Style preset ready: id={preset.id}, name={preset.name}")
    finally:
        db.close()


if __name__ == "__main__":
    main()

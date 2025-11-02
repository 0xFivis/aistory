"""Utility helpers for applying style presets to task configuration."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.style_preset import StylePreset

def merge_style_preset(
    db: Session,
    task_config: Optional[Dict[str, Any]],
) -> Tuple[Dict[str, Any], Dict[str, Any], Optional[StylePreset]]:
    """Merge a style preset into the task configuration if applicable."""
    config: Dict[str, Any] = deepcopy(task_config) if isinstance(task_config, dict) else {}
    storyboard_cfg = config.get("storyboard") if isinstance(config.get("storyboard"), dict) else {}

    preset_id = storyboard_cfg.get("style_preset_id") or config.get("style_preset_id")
    preset: Optional[StylePreset] = None

    if preset_id is not None:
        try:
            preset_id_int = int(preset_id)
        except (TypeError, ValueError):
            preset_id_int = None
        if preset_id_int:
            preset = (
                db.query(StylePreset)
                .filter(StylePreset.id == preset_id_int, StylePreset.is_active == True)
                .first()
            )

    if preset:
        storyboard_cfg["style_preset_id"] = preset.id
        config["style_preset_id"] = preset.id

        if preset.prompt_example:
            storyboard_cfg.setdefault("prompt_example", preset.prompt_example)
            config.setdefault("storyboard_prompt_example", preset.prompt_example)
            config.setdefault("liblib_prompt_example", preset.prompt_example)
        if preset.trigger_words:
            storyboard_cfg.setdefault("trigger_words", preset.trigger_words)
            config.setdefault("storyboard_trigger_words", preset.trigger_words)
            config.setdefault("liblib_trigger_words", preset.trigger_words)
        if preset.word_count_strategy:
            storyboard_cfg.setdefault("word_count_strategy", preset.word_count_strategy)
            config.setdefault("word_count_strategy", preset.word_count_strategy)
        if preset.channel_identity:
            storyboard_cfg.setdefault("channel_identity", preset.channel_identity)
            config.setdefault("channel_identity", preset.channel_identity)
        if preset.lora_id:
            config.setdefault("lora_id", preset.lora_id)
        if preset.checkpoint_id:
            config.setdefault("checkpoint_id", preset.checkpoint_id)

        style_meta_obj = config.get("style_meta")
        if isinstance(style_meta_obj, dict):
            style_meta = style_meta_obj
        else:
            style_meta = {}
            config["style_meta"] = style_meta

        if isinstance(preset.meta, dict):
            for key, value in preset.meta.items():
                style_meta.setdefault(key, value)

        providers_value = config.get("providers")
        if isinstance(providers_value, dict):
            providers_map = providers_value
        else:
            providers_map = {}
            config["providers"] = providers_map

        if preset.image_provider:
            providers_map.setdefault("image", preset.image_provider)
        if preset.video_provider:
            providers_map.setdefault("video", preset.video_provider)

        runninghub_value = style_meta.get("runninghub")
        if isinstance(runninghub_value, dict):
            runninghub_meta = runninghub_value
        else:
            runninghub_meta = {}
            style_meta["runninghub"] = runninghub_meta

        if preset.image_provider == "runninghub" and preset.runninghub_image_workflow_id:
            runninghub_meta.setdefault("image_workflow_config_id", preset.runninghub_image_workflow_id)
        if preset.video_provider == "runninghub" and preset.runninghub_video_workflow_id:
            runninghub_meta.setdefault("video_workflow_config_id", preset.runninghub_video_workflow_id)
    else:
        if "style_preset_id" in config and not config.get("style_preset_id"):
            config.pop("style_preset_id")
        if "style_preset_id" in storyboard_cfg and not storyboard_cfg.get("style_preset_id"):
            storyboard_cfg.pop("style_preset_id")

    config["storyboard"] = storyboard_cfg
    return config, storyboard_cfg, preset


__all__ = ["merge_style_preset"]

from __future__ import annotations

from dataclasses import dataclass
import math
import random
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.subtitle_document import SubtitleDocument
from app.services.base import BaseService
from app.services.storage_service import StorageReference, StorageService
from app.services.faster_whisper_service import TranscriptionResult
from app.services.subtitle_style_constants import DEFAULT_STYLE_VALUES, STYLE_KEY_ALIASES
from app.services.subtitle_style_service import SubtitleStyleConfig, SubtitleStyleService


ASS_STYLE_FORMAT: Tuple[str, ...] = (
    "Name",
    "Fontname",
    "Fontsize",
    "PrimaryColour",
    "SecondaryColour",
    "OutlineColour",
    "BackColour",
    "Bold",
    "Italic",
    "Underline",
    "StrikeOut",
    "ScaleX",
    "ScaleY",
    "Spacing",
    "Angle",
    "BorderStyle",
    "Outline",
    "Shadow",
    "Alignment",
    "MarginL",
    "MarginR",
    "MarginV",
    "Encoding",
)

ASS_EVENT_FORMAT: Tuple[str, ...] = (
    "Layer",
    "Start",
    "End",
    "Style",
    "Name",
    "MarginL",
    "MarginR",
    "MarginV",
    "Effect",
    "Text",
)

POSITION_PATTERN = re.compile(r"\\pos\(\s*([-+]?\d+(?:\.\d+)?)\s*,\s*([-+]?\d+(?:\.\d+)?)\s*\)", re.IGNORECASE)
MOVE_PATTERN = re.compile(
    r"\\move\(\s*([-+]?\d+)\s*,\s*([-+]?\d+)\s*,\s*([-+]?\d+)\s*,\s*([-+]?\d+)(?:\s*,\s*([-+]?\d+)\s*,\s*([-+]?\d+))?\s*\)",
    re.IGNORECASE,
)

DEFAULT_STYLE_VALUES: Dict[str, str] = {
    "Name": "Subtitle",
    "Fontname": "Microsoft YaHei",
    "Fontsize": "48",
    "PrimaryColour": "&H00FFFFFF",
    "SecondaryColour": "&H000000FF",
    "OutlineColour": "&H00000000",
    "BackColour": "&H64000000",
    "Bold": "0",
    "Italic": "0",
    "Underline": "0",
    "StrikeOut": "0",
    "ScaleX": "100",
    "ScaleY": "100",
    "Spacing": "0",
    "Angle": "0",
    "BorderStyle": "1",
    "Outline": "3",
    "Shadow": "0",
    "Alignment": "2",
    "MarginL": "60",
    "MarginR": "60",
    "MarginV": "45",
    "Encoding": "1",
}

STYLE_KEY_ALIASES: Dict[str, str] = {
    "name": "Name",
    "stylename": "Name",
    "fontname": "Fontname",
    "font": "Fontname",
    "fontfamily": "Fontname",
    "font_size": "Fontsize",
    "fontsize": "Fontsize",
    "primarycolour": "PrimaryColour",
    "primarycolor": "PrimaryColour",
    "secondarycolour": "SecondaryColour",
    "secondarycolor": "SecondaryColour",
    "outlinecolour": "OutlineColour",
    "outlinecolor": "OutlineColour",
    "backcolour": "BackColour",
    "backcolor": "BackColour",
    "bold": "Bold",
    "italic": "Italic",
    "underline": "Underline",
    "strikeout": "StrikeOut",
    "scalex": "ScaleX",
    "scaley": "ScaleY",
    "spacing": "Spacing",
    "angle": "Angle",
    "borderstyle": "BorderStyle",
    "outline": "Outline",
    "shadow": "Shadow",
    "alignment": "Alignment",
    "marginl": "MarginL",
    "marginleft": "MarginL",
    "marginr": "MarginR",
    "marginright": "MarginR",
    "marginv": "MarginV",
    "margintop": "MarginV",
    "encoding": "Encoding",
}

SCRIPT_KEY_ALIASES: Dict[str, str] = {
    "playresx": "play_res_x",
    "play_res_x": "play_res_x",
    "playresy": "play_res_y",
    "play_res_y": "play_res_y",
    "wrapstyle": "wrap_style",
    "wrap_style": "wrap_style",
    "scaledborderandshadow": "scaled_border_and_shadow",
    "scaled_border_and_shadow": "scaled_border_and_shadow",
    "title": "title",
    "ycbcrmatrix": "ycbcr_matrix",
    "ycbcr_matrix": "ycbcr_matrix",
}

ASS_RENDER_DEFAULTS: Dict[str, Any] = {
    "title": "Generated Subtitles",
    "play_res_x": 1920,
    "play_res_y": 1080,
    "wrap_style": 1,
    "scaled_border_and_shadow": True,
    "ycbcr_matrix": "TV.601",
}

BooleanStyleFields = {"Bold", "Italic", "Underline", "StrikeOut"}
IntegerFields = {"Alignment", "BorderStyle", "MarginL", "MarginR", "MarginV", "Encoding"}
FloatFields = {"Fontsize", "ScaleX", "ScaleY", "Spacing", "Angle", "Outline", "Shadow"}


@dataclass
class SubtitlePersistenceResult:
    document: SubtitleDocument
    srt_reference: Optional[StorageReference]
    ass_reference: Optional[StorageReference]
    style_name: str
    force_style: Optional[str]
    render_settings: Dict[str, Any]
    segments: List[Dict[str, Any]]


class SubtitleService(BaseService):
    """Manage structured subtitles, rendering, and persistence."""

    def __init__(self):
        super().__init__()
        self.storage = StorageService(self.settings)
        self.style_service = SubtitleStyleService()

    @property
    def service_name(self) -> str:
        return "SubtitleService"

    def _validate_configuration(self) -> None:
        # StorageService already validates configuration.
        pass

    # Public API -----------------------------------------------------

    def persist_transcription(
        self,
        db: Session,
        *,
        task_id: int,
        transcription: TranscriptionResult,
        asset_type: str = "subtitles",
        style_snapshot: Optional[Dict[str, Any]] = None,
        style_override: Optional[Dict[str, Any]] = None,
        ass_overrides: Optional[Dict[str, Any]] = None,
        source_video: Optional[str] = None,
    ) -> SubtitlePersistenceResult:
        segments = self._build_segments(transcription)
        style_config = self._resolve_style_config(style_snapshot, style_override)
        style_payload = style_config.payload
        render_settings = self._build_render_settings(style_payload, ass_overrides)
        style_name = self._resolve_style_name(style_snapshot, style_payload)
        style_fields = self._build_style_fields(style_name, style_payload)
        force_style = self._build_force_style(style_fields)

        ass_content = self._render_ass(segments, style_fields, render_settings, style_payload)
        srt_content = transcription.to_srt()

        document = self._upsert_document(
            db,
            task_id=task_id,
            transcription=transcription,
            segments=segments,
            style_snapshot=style_snapshot,
            style_payload=style_payload,
            style_sections={
                "style_fields": style_config.style_fields,
                "script_settings": style_config.script_settings,
                "effect_settings": style_config.effect_settings,
            },
            style_name=style_name,
            ass_render=render_settings,
            force_style=force_style,
            source_video=source_video,
        )

        prev_srt_api_path = document.srt_api_path
        prev_ass_api_path = document.ass_api_path

        srt_reference = self.storage.save_text(asset_type, srt_content, suffix=".srt")
        document.srt_api_path = srt_reference.api_path
        document.srt_relative_path = srt_reference.relative_path
        document.srt_public_url = None

        ass_reference = self.storage.save_text(asset_type, ass_content, suffix=".ass")
        document.ass_api_path = ass_reference.api_path
        document.ass_relative_path = ass_reference.relative_path
        document.ass_public_url = None

        db.flush()

        if prev_srt_api_path and prev_srt_api_path != document.srt_api_path:
            self._delete_asset(prev_srt_api_path)
        if prev_ass_api_path and prev_ass_api_path != document.ass_api_path:
            self._delete_asset(prev_ass_api_path)

        return SubtitlePersistenceResult(
            document=document,
            srt_reference=srt_reference,
            ass_reference=ass_reference,
            style_name=style_name,
            force_style=force_style,
            render_settings=render_settings,
            segments=segments,
        )

    # Internal helpers ----------------------------------------------

    def _build_segments(self, transcription: TranscriptionResult) -> List[Dict[str, Any]]:
        segments: List[Dict[str, Any]] = []
        for segment in transcription.segments:
            start = self._safe_time(getattr(segment, "start", 0.0))
            end = self._safe_time(getattr(segment, "end", start))
            if end < start:
                end = start
            duration = max(end - start, 0.0)

            words_payload: List[Dict[str, Any]] = []
            words = getattr(segment, "words", None)
            if words:
                for word in words:
                    word_text = str(getattr(word, "text", getattr(word, "word", ""))).strip()
                    word_start = self._safe_time(getattr(word, "start", start))
                    word_end = self._safe_time(getattr(word, "end", word_start))
                    if word_end < word_start:
                        word_end = word_start
                    words_payload.append(
                        {
                            "start": round(word_start, 3),
                            "end": round(word_end, 3),
                            "text": word_text,
                        }
                    )

            text = str(getattr(segment, "text", "")).strip()
            segments.append(
                {
                    "index": int(getattr(segment, "index", len(segments) + 1)),
                    "start": round(start, 3),
                    "end": round(end, 3),
                    "duration": round(duration, 3),
                    "text": text,
                    "words": words_payload,
                }
            )
        return segments

    def _resolve_style_config(
        self,
        style_snapshot: Optional[Dict[str, Any]],
        style_override: Optional[Dict[str, Any]],
    ) -> SubtitleStyleConfig:
        style_fields: Dict[str, Any] = {}
        script_settings: Dict[str, Any] = {}
        effect_settings: Dict[str, Any] = {}
        raw_payload: Dict[str, Any] = {}

        if isinstance(style_snapshot, dict):
            snapshot_style_fields = style_snapshot.get("style_fields")
            if isinstance(snapshot_style_fields, dict):
                style_fields.update(snapshot_style_fields)

            snapshot_script = style_snapshot.get("script_settings")
            if isinstance(snapshot_script, dict):
                script_settings.update(snapshot_script)

            snapshot_effects = style_snapshot.get("effect_settings")
            if isinstance(snapshot_effects, dict):
                effect_settings.update(snapshot_effects)

            snapshot_style = style_snapshot.get("style")
            if isinstance(snapshot_style, dict) and not style_fields:
                style_fields.update(snapshot_style)

            snapshot_payload = style_snapshot.get("style_payload")
            if isinstance(snapshot_payload, dict):
                raw_payload.update(snapshot_payload)

        if isinstance(style_override, dict):
            override_style_fields = style_override.get("style_fields")
            if isinstance(override_style_fields, dict):
                style_fields.update(override_style_fields)

            override_script = style_override.get("script_settings")
            if isinstance(override_script, dict):
                script_settings.update(override_script)

            override_effects = style_override.get("effect_settings")
            if isinstance(override_effects, dict):
                effect_settings.update(override_effects)

            override_payload = style_override.get("style_payload")
            if isinstance(override_payload, dict):
                raw_payload.update(override_payload)

            for key, value in style_override.items():
                if key in {"style_fields", "script_settings", "effect_settings", "style_payload"}:
                    continue
                raw_payload[key] = value

        return self.style_service.normalise_payload(
            style_fields=style_fields,
            script_settings=script_settings,
            effect_settings=effect_settings,
            raw_payload=raw_payload,
        )

    def _build_render_settings(
        self,
        style_payload: Dict[str, Any],
        ass_overrides: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        render_settings = dict(ASS_RENDER_DEFAULTS)

        for key, value in style_payload.items():
            alias_key = SCRIPT_KEY_ALIASES.get(self._normalise_key(str(key)))
            if alias_key:
                render_settings[alias_key] = value

        if ass_overrides and isinstance(ass_overrides, dict):
            for key, value in ass_overrides.items():
                alias_key = SCRIPT_KEY_ALIASES.get(self._normalise_key(str(key)))
                if not alias_key:
                    continue
                render_settings[alias_key] = value

        render_settings["play_res_x"] = self._safe_int(render_settings.get("play_res_x"), default=1920)
        render_settings["play_res_y"] = self._safe_int(render_settings.get("play_res_y"), default=1080)
        render_settings["wrap_style"] = self._safe_int(render_settings.get("wrap_style"), default=1)
        scaled = render_settings.get("scaled_border_and_shadow")
        render_settings["scaled_border_and_shadow"] = bool(
            str(scaled).lower() not in {"false", "0", "no"}
        )
        title = render_settings.get("title")
        if not isinstance(title, str) or not title.strip():
            render_settings["title"] = ASS_RENDER_DEFAULTS["title"]
        ycbcr_matrix = render_settings.get("ycbcr_matrix")
        if not isinstance(ycbcr_matrix, str) or not ycbcr_matrix.strip():
            render_settings["ycbcr_matrix"] = ASS_RENDER_DEFAULTS["ycbcr_matrix"]
        return render_settings

    def _resolve_style_name(
        self,
        style_snapshot: Optional[Dict[str, Any]],
        style_payload: Dict[str, Any],
    ) -> str:
        candidates: List[str] = []
        if isinstance(style_snapshot, dict):
            if isinstance(style_snapshot.get("name"), str):
                candidates.append(str(style_snapshot["name"]))
            snapshot_style = style_snapshot.get("style")
            snapshot_style_fields = style_snapshot.get("style_fields")
        else:
            snapshot_style = None
            snapshot_style_fields = None
        if isinstance(snapshot_style, dict):
            raw = snapshot_style.get("Name") or snapshot_style.get("StyleName")
            if isinstance(raw, str):
                candidates.append(raw)
        if isinstance(snapshot_style_fields, dict):
            raw = snapshot_style_fields.get("Name") or snapshot_style_fields.get("StyleName")
            if isinstance(raw, str):
                candidates.append(raw)
        payload_name = style_payload.get("Name") or style_payload.get("StyleName")
        if isinstance(payload_name, str):
            candidates.append(payload_name)
        meta = style_payload.get("_meta") if isinstance(style_payload.get("_meta"), dict) else None
        if isinstance(meta, dict):
            meta_style = meta.get("style")
            if isinstance(meta_style, dict):
                raw = meta_style.get("Name") or meta_style.get("StyleName")
                if isinstance(raw, str):
                    candidates.append(raw)

        for candidate in candidates:
            sanitized = self._sanitize_style_name(candidate)
            if sanitized:
                return sanitized
        return self._sanitize_style_name(None)

    def _build_style_fields(
        self,
        style_name: str,
        style_payload: Dict[str, Any],
    ) -> Dict[str, str]:
        fields = dict(DEFAULT_STYLE_VALUES)
        fields["Name"] = style_name

        for key, value in style_payload.items():
            alias = STYLE_KEY_ALIASES.get(self._normalise_key(str(key)))
            if not alias:
                continue
            if alias in BooleanStyleFields:
                fields[alias] = "-1" if self._as_bool(value) else "0"
            elif alias in IntegerFields:
                fields[alias] = str(self._safe_int(value, default=int(fields[alias])))
            elif alias in FloatFields:
                fields[alias] = self._format_float(value, default=float(fields[alias]))
            else:
                fields[alias] = str(value)
        return fields

    def _build_force_style(self, style_fields: Dict[str, str]) -> str:
        pairs: List[str] = []
        for key, value in style_fields.items():
            if key == "Name":
                continue
            pairs.append(f"{key}={value}")
        return ",".join(pairs)

    def _render_ass(
        self,
        segments: Iterable[Dict[str, Any]],
        style_fields: Dict[str, str],
        render_settings: Dict[str, Any],
        style_payload: Dict[str, Any],
    ) -> str:
        lines: List[str] = []
        lines.append("[Script Info]")
        lines.append(f"Title: {render_settings['title']}")
        lines.append("ScriptType: v4.00+")
        lines.append("Collisions: Normal")
        lines.append(f"PlayResX: {render_settings['play_res_x']}")
        lines.append(f"PlayResY: {render_settings['play_res_y']}")
        lines.append(f"LayoutResX: {render_settings['play_res_x']}")
        lines.append(f"LayoutResY: {render_settings['play_res_y']}")
        lines.append(f"WrapStyle: {render_settings['wrap_style']}")
        scaled = "yes" if render_settings.get("scaled_border_and_shadow") else "no"
        lines.append(f"ScaledBorderAndShadow: {scaled}")
        lines.append(f"YCbCr Matrix: {render_settings['ycbcr_matrix']}")
        lines.append("")

        lines.append("[V4+ Styles]")
        lines.append("Format: " + ",".join(ASS_STYLE_FORMAT))
        style_values = [style_fields.get(field, DEFAULT_STYLE_VALUES[field]) for field in ASS_STYLE_FORMAT]
        lines.append("Style: " + ",".join(style_values))
        lines.append("")

        lines.append("[Events]")
        lines.append("Format: " + ",".join(ASS_EVENT_FORMAT))

        margin_l = style_fields.get("MarginL", "0")
        margin_r = style_fields.get("MarginR", "0")
        margin_v = style_fields.get("MarginV", "0")
        style_name = style_fields.get("Name", "Subtitle")
        sequence_mode = self._extract_sequence_mode(style_payload)
        effect_field, base_override, move_config = self._build_effect_overrides(style_payload, sequence_mode)

        events = self._generate_ass_events(
            segments=segments,
            style_payload=style_payload,
            render_settings=render_settings,
            text_override=base_override,
            style_fields=style_fields,
            sequence_mode=sequence_mode,
            base_move_config=move_config,
        )

        alignment_variant = self._normalise_alignment_variant(style_payload)
        variant_anchor: Optional[Tuple[float, float]] = None
        if alignment_variant == "center-lower" and not self._parse_override_position(base_override):
            variant_anchor = self._resolve_alignment_anchor(style_fields, style_payload, render_settings)

        if variant_anchor is not None:
            pos_override = f"\\pos({int(round(variant_anchor[0]))},{int(round(variant_anchor[1]))})"
            for event in events:
                if event.get("extra_override"):
                    continue
                event["extra_override"] = pos_override

        for event in events:
            start = self._format_ass_timestamp(event.get("start"))
            end = self._format_ass_timestamp(event.get("end"))
            text = event.get("text", "")
            extra_override = event.get("extra_override")
            override_block = self._merge_override_blocks(base_override, extra_override)
            if override_block:
                text = f"{override_block}{text}"
            dialogue = [
                "0",
                start,
                end,
                style_name,
                "",
                margin_l,
                margin_r,
                margin_v,
                effect_field,
                text,
            ]
            lines.append("Dialogue: " + ",".join(dialogue))
        lines.append("")
        return "\n".join(lines)

    def _build_effect_overrides(
        self,
        style_payload: Dict[str, Any],
        sequence_mode: str,
    ) -> Tuple[str, str, Optional[Dict[str, Any]]]:
        if not isinstance(style_payload, dict):
            return "", "", None

        effect_value = ""
        text_tags: List[str] = []
        move_override, move_config = self._extract_move_components(style_payload)

        blur_raw = style_payload.get("Blur")
        blur_value: Optional[float] = None
        if isinstance(blur_raw, (int, float)):
            blur_value = float(blur_raw)
        elif isinstance(blur_raw, str):
            try:
                blur_value = float(blur_raw)
            except (TypeError, ValueError):
                blur_value = None
        if blur_value is not None and not math.isnan(blur_value):
            text_tags.append(f"\\blur{blur_value:g}")

        for key in ("Animation", "Move", "Fade", "TextOverride"):
            raw = style_payload.get(key)
            if key == "Move" and move_override is not None:
                raw = move_override
            if not raw:
                continue
            text = str(raw).strip()
            if not text:
                continue
            if text.startswith("{") and text.endswith("}"):
                text = text[1:-1]
            if not text.startswith("\\"):
                text = "\\" + text.lstrip("\\")
            if key == "Move" and sequence_mode == "word-continuous" and move_config:
                continue
            text_tags.append(text)

        effect_raw = style_payload.get("Effect")
        if isinstance(effect_raw, str) and effect_raw.strip():
            effect_value = effect_raw.strip()

        text_override = ""
        if text_tags:
            alignment_variant = self._normalise_alignment_variant(style_payload)
            if alignment_variant == "center-lower":
                cleaned_tags: List[str] = []
                for tag in text_tags:
                    if not tag:
                        continue
                    stripped = re.sub(r"\\pos\([^{}]*?\)", "", tag)
                    stripped = stripped.strip()
                    if stripped:
                        cleaned_tags.append(stripped)
                text_tags = cleaned_tags
            if text_tags:
                text_override = "{" + "".join(text_tags) + "}"

        return effect_value, text_override, move_config

    def _generate_ass_events(
        self,
        *,
        segments: Iterable[Dict[str, Any]],
        style_payload: Dict[str, Any],
        render_settings: Dict[str, Any],
        text_override: str,
        style_fields: Dict[str, str],
        sequence_mode: str,
        base_move_config: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        text_case = self._extract_text_case(style_payload)
        strip_punctuation = self._should_strip_punctuation(style_payload, sequence_mode)
        if sequence_mode == "word-continuous":
            events = self._generate_word_sequence_events(
                segments=segments,
                style_payload=style_payload,
                render_settings=render_settings,
                base_override=text_override,
                style_fields=style_fields,
                base_move_config=base_move_config,
                text_case=text_case,
                strip_punctuation=strip_punctuation,
            )
        else:
            events = []
            for segment in segments:
                start = self._safe_time(segment.get("start"))
                end = self._safe_time(segment.get("end", start))
                if end < start:
                    end = start
                raw_text = self._prepare_text_content(segment.get("text", ""), text_case, strip_punctuation)
                text = self._sanitize_ass_text(raw_text)
                events.append({
                    "start": start,
                    "end": end,
                    "text": text,
                })
        if not events:
            events.append({
                "start": 0.0,
                "end": 0.0,
                "text": "",
            })
        return events

    def _generate_word_sequence_events(
        self,
        *,
        segments: Iterable[Dict[str, Any]],
        style_payload: Dict[str, Any],
        render_settings: Dict[str, Any],
        base_override: str,
        style_fields: Dict[str, Any],
        base_move_config: Optional[Dict[str, Any]],
        text_case: str,
        strip_punctuation: bool,
    ) -> List[Dict[str, Any]]:
        events: List[Dict[str, Any]] = []
        anchor = self._extract_sequence_anchor(style_payload, base_override, render_settings, style_fields)
        jitter = self._extract_sequence_jitter(style_payload)

        base_has_position = bool(self._parse_override_position(base_override))

        for seg_index, segment in enumerate(segments):
            segment_start = self._safe_time(segment.get("start"))
            segment_end = self._safe_time(segment.get("end", segment_start))
            if segment_end < segment_start:
                segment_end = segment_start
            segment_duration = max(segment_end - segment_start, 0.0)

            prepared_words: List[Tuple[float, float, str]] = []
            raw_words = segment.get("words")
            if isinstance(raw_words, list) and raw_words:
                word_count = len(raw_words)
                for word_index, word in enumerate(raw_words):
                    word_start = max(self._safe_time(word.get("start", segment_start)), segment_start)
                    word_end = self._safe_time(word.get("end", word_start))
                    if word_end <= word_start:
                        fallback = segment_duration / max(word_count, 1)
                        if fallback <= 0:
                            fallback = 0.35
                        word_end = word_start + fallback
                    prepared = self._prepare_text_content(word.get("text", ""), text_case, strip_punctuation)
                    if not prepared:
                        continue
                    sanitized = self._sanitize_ass_text(prepared)
                    if not sanitized:
                        continue
                    prepared_words.append((word_start, word_end, sanitized))

            if not prepared_words:
                tokens = self._split_sequence_text(segment.get("text", ""))
                if tokens:
                    if segment_duration <= 0:
                        segment_duration = max(len(tokens) * 0.45, 0.35)
                        segment_end = segment_start + segment_duration
                    per_word = segment_duration / max(len(tokens), 1)
                    per_word = min(max(per_word, 0.35), 0.8)
                    cursor = segment_start
                    target_end = segment_start + segment_duration
                    for idx, token in enumerate(tokens):
                        start_time = cursor
                        end_time = cursor + per_word
                        if idx == len(tokens) - 1:
                            end_time = max(end_time, target_end)
                        if end_time <= start_time:
                            end_time = start_time + 0.35
                        cursor = end_time
                        prepared = self._prepare_text_content(token, text_case, strip_punctuation)
                        if prepared:
                            sanitized = self._sanitize_ass_text(prepared)
                            if sanitized:
                                prepared_words.append((start_time, end_time, sanitized))

            if prepared_words:
                for word_index, (word_start, word_end, text) in enumerate(prepared_words):
                    extra_override = self._build_sequence_move(
                        anchor=anchor,
                        jitter=jitter,
                        start=word_start,
                        end=word_end,
                        segment_index=seg_index,
                        word_index=word_index,
                        include_pos=not base_has_position,
                        base_move=base_move_config,
                    )
                    events.append({
                        "start": word_start,
                        "end": word_end,
                        "text": text,
                        "extra_override": extra_override,
                    })
            else:
                prepared = self._prepare_text_content(segment.get("text", ""), text_case, strip_punctuation)
                text = self._sanitize_ass_text(prepared)
                events.append({
                    "start": segment_start,
                    "end": segment_end,
                    "text": text,
                })

        return events

    @staticmethod
    def _merge_override_blocks(base: str, extra: Optional[str]) -> str:
        tags: List[str] = []
        for value in (base, extra):
            if not value:
                continue
            text = str(value)
            if text.startswith("{") and text.endswith("}"):
                text = text[1:-1]
            if text:
                tags.append(text)
        if not tags:
            return ""
        return "{" + "".join(tags) + "}"

    @staticmethod
    def _get_effect_value(style_payload: Dict[str, Any], key: str) -> Any:
        if not isinstance(style_payload, dict):
            return None
        if key in style_payload:
            return style_payload.get(key)
        meta = style_payload.get("_meta")
        if isinstance(meta, dict):
            effects = meta.get("effects")
            if isinstance(effects, dict) and key in effects:
                return effects.get(key)
        return None

    @staticmethod
    def _get_structured_effect(style_payload: Dict[str, Any], key: str) -> Optional[Dict[str, Any]]:
        if not isinstance(style_payload, dict):
            return None
        meta = style_payload.get("_meta")
        if not isinstance(meta, dict):
            return None
        structured = meta.get("effects_structured")
        if not isinstance(structured, dict):
            return None
        value = structured.get(key)
        return value if isinstance(value, dict) else None

    @staticmethod
    def _parse_move_config(value: str) -> Optional[Dict[str, Any]]:
        if not value:
            return None
        text = value.strip()
        if text.startswith("{") and text.endswith("}"):
            text = text[1:-1].strip()
        match = MOVE_PATTERN.search(text)
        if not match:
            return None
        try:
            x1 = int(match.group(1))
            y1 = int(match.group(2))
            x2 = int(match.group(3))
            y2 = int(match.group(4))
        except (TypeError, ValueError):
            return None
        config: Dict[str, Any] = {
            "from": {"x": x1, "y": y1},
            "to": {"x": x2, "y": y2},
        }
        t1_raw = match.group(5)
        t2_raw = match.group(6)
        if t1_raw is not None or t2_raw is not None:
            try:
                t1 = max(int(t1_raw) if t1_raw is not None else 0, 0)
            except (TypeError, ValueError):
                t1 = 0
            try:
                t2 = int(t2_raw) if t2_raw is not None else t1
            except (TypeError, ValueError):
                t2 = t1
            t2 = max(t2, t1)
            config["t1"] = t1
            config["t2"] = t2
        return config

    def _extract_move_components(self, style_payload: Dict[str, Any]) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        override_value: Optional[str] = None
        config_value: Optional[Dict[str, Any]] = None
        if not isinstance(style_payload, dict):
            return override_value, config_value

        raw_override = style_payload.get("Move")
        if isinstance(raw_override, str) and raw_override.strip():
            override_value = raw_override.strip()

        structured = self._get_structured_effect(style_payload, "Move")
        if isinstance(structured, dict):
            config_value = structured

        if config_value is None and override_value:
            config_value = self._parse_move_config(override_value)

        return override_value, config_value

    def _extract_sequence_mode(self, style_payload: Dict[str, Any]) -> str:
        value = self._get_effect_value(style_payload, "SequenceMode")
        if isinstance(value, str):
            text = value.strip().lower()
            if not text or text in {"none", "off", "false"}:
                return ""
            mapped = {
                "word": "word-continuous",
                "word-continuous": "word-continuous",
                "wordcontinuous": "word-continuous",
                "word_sequence": "word-continuous",
                "wordsequence": "word-continuous",
            }
            return mapped.get(text, text)
        return ""

    def _extract_sequence_jitter(self, style_payload: Dict[str, Any]) -> Tuple[float, float]:
        value = self._get_effect_value(style_payload, "SequenceJitter")
        if value is None:
            return 2.0, 2.0

        if isinstance(value, dict):
            dx = self._safe_float(value.get("dx"))
            dy = self._safe_float(value.get("dy"))
        elif isinstance(value, (list, tuple)) and len(value) >= 2:
            dx = self._safe_float(value[0])
            dy = self._safe_float(value[1])
        elif isinstance(value, str):
            parts = re.split(r"[\s,]+", value.strip())
            if len(parts) >= 2:
                dx = self._safe_float(parts[0])
                dy = self._safe_float(parts[1])
            else:
                number = self._safe_float(parts[0]) if parts else 0.0
                dx = dy = number
        else:
            number = self._safe_float(value)
            dx = dy = number

        dx = max(dx if dx is not None else 0.0, 0.0)
        dy = max(dy if dy is not None else 0.0, 0.0)
        return dx, dy

    def _normalise_alignment_variant(self, style_payload: Dict[str, Any]) -> str:
        value = self._get_effect_value(style_payload, "AlignmentVariant")
        if isinstance(value, str):
            text = value.strip().lower()
            if not text:
                return ""
            if text in {"center-lower", "center_lower", "centre-lower", "centerlower"}:
                return "center-lower"
        return ""

    def _resolve_alignment_anchor(
        self,
        style_fields: Dict[str, Any],
        style_payload: Dict[str, Any],
        render_settings: Dict[str, Any],
    ) -> Tuple[float, float]:
        alignment_raw = style_fields.get("Alignment")
        if alignment_raw is None:
            alignment_raw = style_payload.get("Alignment")
        alignment = self._safe_int(alignment_raw, default=2)

        margin_l_raw = style_fields.get("MarginL")
        if margin_l_raw is None:
            margin_l_raw = style_payload.get("MarginL")
        margin_r_raw = style_fields.get("MarginR")
        if margin_r_raw is None:
            margin_r_raw = style_payload.get("MarginR")
        margin_v_raw = style_fields.get("MarginV")
        if margin_v_raw is None:
            margin_v_raw = style_payload.get("MarginV")

        margin_l = max(self._safe_int(margin_l_raw, default=60), 0)
        margin_r = max(self._safe_int(margin_r_raw, default=60), 0)
        margin_v = max(self._safe_int(margin_v_raw, default=45), 0)

        width = max(self._safe_float(render_settings.get("play_res_x"), default=1920.0), 1.0)
        height = max(self._safe_float(render_settings.get("play_res_y"), default=1080.0), 1.0)

        horizontal = ((alignment - 1) % 3 + 3) % 3
        vertical = (alignment - 1) // 3

        if horizontal == 0:
            x = float(margin_l)
        elif horizontal == 2:
            x = max(width - float(margin_r), 0.0)
        else:
            x = width / 2.0

        if vertical <= 0:
            y = max(height - float(margin_v), 0.0)
        elif vertical == 1:
            y = height / 2.0
        else:
            y = float(margin_v)

        variant = self._normalise_alignment_variant(style_payload)
        if variant == "center-lower":
            bottom_y = max(height - float(margin_v), 0.0)
            y = (y + bottom_y) / 2.0
        return float(x), float(y)

    def _extract_sequence_anchor(
        self,
        style_payload: Dict[str, Any],
        base_override: str,
        render_settings: Dict[str, Any],
        style_fields: Dict[str, Any],
    ) -> Tuple[float, float]:
        pos = self._parse_override_position(base_override)
        if pos:
            return pos

        fallback_x, fallback_y = self._resolve_alignment_anchor(style_fields, style_payload, render_settings)

        value = self._get_effect_value(style_payload, "SequenceAnchor")
        if isinstance(value, dict):
            x_val = self._safe_float(value.get("x"), default=fallback_x)
            y_val = self._safe_float(value.get("y"), default=fallback_y)
            return x_val, y_val
        if isinstance(value, (list, tuple)) and len(value) >= 2:
            x_val = self._safe_float(value[0], default=fallback_x)
            y_val = self._safe_float(value[1], default=fallback_y)
            return x_val, y_val
        if isinstance(value, str):
            parts = re.split(r"[\s,]+", value.strip())
            if len(parts) >= 2:
                x_val = self._safe_float(parts[0], default=fallback_x)
                y_val = self._safe_float(parts[1], default=fallback_y)
                return x_val, y_val


    def _extract_text_case(self, style_payload: Dict[str, Any]) -> str:
        value = self._get_effect_value(style_payload, "TextCase")
        if isinstance(value, str):
            text = value.strip().lower()
            if text == "upper":
                return "upper"
            if text == "lower":
                return "lower"
        return "none"

    def _should_strip_punctuation(self, style_payload: Dict[str, Any], sequence_mode: str) -> bool:
        value = self._get_effect_value(style_payload, "StripPunctuation")
        if value is None:
            return sequence_mode == "word-continuous"
        return self._as_bool(value)

    def _prepare_text_content(self, value: Any, text_case: str, strip_punctuation: bool) -> str:
        raw = "" if value is None else str(value)
        if strip_punctuation:
            raw = "".join(ch for ch in raw if not unicodedata.category(ch).startswith("P"))
            raw = re.sub(r"\s{2,}", " ", raw)
        if text_case == "upper":
            raw = raw.upper()
        elif text_case == "lower":
            raw = raw.lower()
        return raw.strip()
        return fallback_x, fallback_y

    @staticmethod
    def _parse_override_position(override_block: str) -> Optional[Tuple[float, float]]:
        if not override_block:
            return None
        text = override_block
        if text.startswith("{") and text.endswith("}"):
            text = text[1:-1]
        match = POSITION_PATTERN.search(text)
        if not match:
            return None
        try:
            x_val = float(match.group(1))
            y_val = float(match.group(2))
        except (TypeError, ValueError):
            return None
        return x_val, y_val

    def _build_sequence_move(
        self,
        *,
        anchor: Tuple[float, float],
        jitter: Tuple[float, float],
        start: float,
        end: float,
        segment_index: int,
        word_index: int,
        include_pos: bool,
        base_move: Optional[Dict[str, Any]] = None,
    ) -> str:
        dx, dy = jitter
        need_move = (dx > 0 or dy > 0) or bool(base_move)

        seed = (segment_index + 1) * 65537 + (word_index + 1) * 131071
        rng = random.Random(seed)

        def _jitter(amplitude: float) -> float:
            if amplitude <= 0:
                return 0.0
            return rng.uniform(-amplitude, amplitude)

        anchor_x = int(round(anchor[0]))
        anchor_y = int(round(anchor[1]))
        start_x = anchor_x + _jitter(dx)
        start_y = anchor_y + _jitter(dy)
        end_x = anchor_x + _jitter(dx)
        end_y = anchor_y + _jitter(dy)
        duration_ms = max(int(round((end - start) * 1000)), 1)
        move_start_time = 0
        move_end_time = duration_ms

        if isinstance(base_move, dict):
            from_point = base_move.get("from") if isinstance(base_move.get("from"), dict) else None
            to_point = base_move.get("to") if isinstance(base_move.get("to"), dict) else None
            if isinstance(from_point, dict) and isinstance(to_point, dict):
                from_x = from_point.get("x")
                from_y = from_point.get("y")
                to_x = to_point.get("x")
                to_y = to_point.get("y")
                if None not in (from_x, from_y, to_x, to_y):
                    start_x += self._safe_int(from_x, default=anchor_x) - self._safe_int(to_x, default=anchor_x)
                    start_y += self._safe_int(from_y, default=anchor_y) - self._safe_int(to_y, default=anchor_y)
            t1_raw = base_move.get("t1")
            t2_raw = base_move.get("t2")
            if t1_raw is not None or t2_raw is not None:
                move_start_time = max(self._safe_int(t1_raw, default=0), 0)
                move_end_time = max(
                    self._safe_int(t2_raw if t2_raw is not None else move_start_time, default=move_start_time),
                    move_start_time,
                )

        move_tag = ""
        if need_move:
            move_tag = (
                f"\\move({int(round(start_x))},{int(round(start_y))},{int(round(end_x))},{int(round(end_y))},{move_start_time},{move_end_time})"
            )

        pos_tag = f"\\pos({anchor_x},{anchor_y})" if include_pos else ""

        if not move_tag and not pos_tag:
            return ""

        tags = [tag for tag in (pos_tag, move_tag) if tag]
        return "{" + "".join(tags) + "}"

    @staticmethod
    def _split_sequence_text(value: Any) -> List[str]:
        if value is None:
            return []
        text = str(value).strip()
        if not text:
            return []
        tokens = re.findall(r"\S+", text)
        return [token for token in tokens if token]

    def _upsert_document(
        self,
        db: Session,
        *,
        task_id: int,
        transcription: TranscriptionResult,
        segments: List[Dict[str, Any]],
        style_snapshot: Optional[Dict[str, Any]],
        style_payload: Dict[str, Any],
        style_sections: Dict[str, Any],
        style_name: str,
        ass_render: Dict[str, Any],
        force_style: Optional[str],
        source_video: Optional[str],
    ) -> SubtitleDocument:
        document = (
            db.query(SubtitleDocument)
            .filter(SubtitleDocument.task_id == task_id)
            .one_or_none()
        )
        if document is None:
            document = SubtitleDocument(
                task_id=task_id,
                segments=segments,
                segment_count=len(segments),
            )
            db.add(document)
        else:
            document.segments = segments
            document.segment_count = len(segments)

        language = transcription.info.get("language") if transcription.info else None
        document.language = language
        document.model_name = transcription.model
        document.text = transcription.text
        preview_text = (transcription.text or "").strip()
        if not preview_text:
            preview_parts = [segment.get("text", "") for segment in segments[:5]]
            preview_text = " ".join([part.strip() for part in preview_parts if part]).strip()
        info_payload: Dict[str, Any] = {
            "language": language,
            "transcription": transcription.info or {},
            "source_video": source_video,
        }
        if preview_text:
            info_payload["text_preview"] = preview_text[:500]
        document.info = info_payload
        document.options = {
            "transcription": transcription.options,
            "style_snapshot": style_snapshot,
            "style_payload": style_payload,
            "style_sections": style_sections,
            "style_name": style_name,
            "ass_render": ass_render,
            "force_style": force_style,
        }
        return document

    def _delete_asset(self, api_path: str) -> None:
        try:
            absolute = self.storage.to_absolute_path(api_path)
        except Exception as exc:  # pragma: no cover - best effort cleanup
            self._log_error(exc, {"operation": "delete_asset", "api_path": api_path})
            return
        try:
            Path(absolute).unlink(missing_ok=True)
        except Exception as exc:  # pragma: no cover - best effort cleanup
            self._log_error(exc, {"operation": "delete_asset", "api_path": api_path})

    # Formatting helpers --------------------------------------------

    @staticmethod
    def _normalise_key(value: str) -> str:
        return value.replace("-", "").replace("_", "").lower()

    @staticmethod
    def _safe_time(value: Any) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return 0.0
        if math.isnan(number) or math.isinf(number):
            return 0.0
        return max(number, 0.0)

    @staticmethod
    def _safe_float(value: Any, *, default: float = 0.0) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return default
        if math.isnan(number) or math.isinf(number):
            return default
        return number

    @staticmethod
    def _safe_int(value: Any, *, default: int = 0) -> int:
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return int(default)

    @staticmethod
    def _format_float(value: Any, *, default: float = 0.0) -> str:
        try:
            number = float(value)
        except (TypeError, ValueError):
            number = default
        if math.isnan(number) or math.isinf(number):
            number = default
        return f"{number:g}"

    @staticmethod
    def _as_bool(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            return value.strip().lower() not in {"", "0", "false", "no"}
        return bool(value)

    @staticmethod
    def _sanitize_style_name(value: Optional[str]) -> str:
        if not value:
            return "Subtitle"
        cleaned = [
            ch if ch.isalnum() or ch in {"_", "-"} else "_"
            for ch in value.strip()
        ]
        name = "".join(cleaned).strip("_")
        return name or "Subtitle"

    @staticmethod
    def _format_ass_timestamp(value: Any) -> str:
        total_centiseconds = int(round(SubtitleService._safe_time(value) * 100))
        hours = total_centiseconds // 360000
        minutes = (total_centiseconds % 360000) // 6000
        seconds = (total_centiseconds % 6000) // 100
        centiseconds = total_centiseconds % 100
        return f"{hours:d}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}"

    @staticmethod
    def _sanitize_ass_text(value: Any) -> str:
        text = str(value or "")
        text = text.replace("\\", r"\\")
        text = text.replace("{", r"\{").replace("}", r"\}")
        text = text.replace("\r", "")
        text = text.replace("\n", r"\N")
        return text


__all__ = ["SubtitleService", "SubtitlePersistenceResult"]

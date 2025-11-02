from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Tuple

from app.services.base import BaseService
from app.services.subtitle_style_constants import DEFAULT_STYLE_VALUES, STYLE_KEY_ALIASES

_STYLE_KEY_CANONICAL = {key: key for key in DEFAULT_STYLE_VALUES.keys()}
_SCRIPT_KEY_CANONICAL = {
    "playresx": "PlayResX",
    "play_res_x": "PlayResX",
    "playresy": "PlayResY",
    "play_res_y": "PlayResY",
    "wrapstyle": "WrapStyle",
    "wrap_style": "WrapStyle",
    "scaledborderandshadow": "ScaledBorderAndShadow",
    "scaled_border_and_shadow": "ScaledBorderAndShadow",
    "title": "Title",
    "ycbcrmatrix": "YCbCrMatrix",
    "ycbcr_matrix": "YCbCrMatrix",
}
_EFFECT_KEY_CANONICAL = {
    "blur": "Blur",
    "animation": "Animation",
    "move": "Move",
    "fade": "Fade",
    "effect": "Effect",
    "textoverride": "TextOverride",
    "text_override": "TextOverride",
    "sequencemode": "SequenceMode",
    "sequence_mode": "SequenceMode",
    "sequencejitter": "SequenceJitter",
    "sequence_jitter": "SequenceJitter",
    "sequenceanchor": "SequenceAnchor",
    "sequence_anchor": "SequenceAnchor",
    "alignmentvariant": "AlignmentVariant",
    "alignment_variant": "AlignmentVariant",
    "textcase": "TextCase",
    "text_case": "TextCase",
    "strippunctuation": "StripPunctuation",
    "strip_punctuation": "StripPunctuation",
}
_COLOR_PATTERN = re.compile(r"^&H[0-9A-Fa-f]{6,8}$")
_MOVE_PATTERN = re.compile(r"\\move\(\s*([-+]?\d+)\s*,\s*([-+]?\d+)\s*,\s*([-+]?\d+)\s*,\s*([-+]?\d+)(?:\s*,\s*([-+]?\d+)\s*,\s*([-+]?\d+)\s*)?\)", re.IGNORECASE)
_FAD_PATTERN = re.compile(r"\\fad\(\s*(\d+)\s*,\s*(\d+)\s*\)", re.IGNORECASE)
_FADE_PATTERN = re.compile(
    r"\\fade\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)",
    re.IGNORECASE,
)
_TRANSFORM_PATTERN = re.compile(r"\\t\(([^()]*)\)", re.IGNORECASE)


@dataclass
class SubtitleStyleConfig:
    payload: Dict[str, Any]
    style_fields: Dict[str, Any]
    script_settings: Dict[str, Any]
    effect_settings: Dict[str, Any]
    effect_overrides: Dict[str, Any]


class SubtitleStyleService(BaseService):
    """Validate and normalise subtitle style payloads."""

    def __init__(self) -> None:
        super().__init__()

    @property
    def service_name(self) -> str:
        return "SubtitleStyleService"

    def _validate_configuration(self) -> None:  # pragma: no cover - no external config required
        # Subtitle style normalisation does not require external configuration.
        return None

    def normalise_payload(
        self,
        *,
        style_fields: Dict[str, Any] | None = None,
        script_settings: Dict[str, Any] | None = None,
        effect_settings: Dict[str, Any] | None = None,
        raw_payload: Dict[str, Any] | None = None,
    ) -> SubtitleStyleConfig:
        raw = raw_payload.copy() if isinstance(raw_payload, dict) else {}
        style_source = {}
        script_source = {}
        effect_source = {}
        if raw:
            style_source.update(self._extract_style_fields(raw))
            script_source.update(self._extract_script_settings(raw))
            effect_source.update(self._extract_effect_settings(raw))
        if style_fields:
            style_source.update(style_fields)
        if script_settings:
            script_source.update(script_settings)
        if effect_settings:
            effect_source.update(effect_settings)

        normalised_style = self._normalise_style_fields(style_source)
        normalised_script = self._normalise_script_settings(script_source)
        normalised_effect, structured_effect = self._normalise_effect_settings(effect_source)

        payload: Dict[str, Any] = {}
        payload.update(normalised_style)
        payload.update(normalised_script)
        payload.update(normalised_effect)
        meta: Dict[str, Any] = {}
        if normalised_style:
            meta["style"] = normalised_style
        if normalised_script:
            meta["script"] = normalised_script
        if normalised_effect:
            meta["effects"] = normalised_effect
        if structured_effect:
            meta["effects_structured"] = structured_effect
        if meta:
            payload["_meta"] = meta

        combined_effect = dict(normalised_effect)
        if structured_effect:
            combined_effect.update(structured_effect)
        return SubtitleStyleConfig(
            payload=payload,
            style_fields=normalised_style,
            script_settings=normalised_script,
            effect_settings=combined_effect,
            effect_overrides=normalised_effect,
        )

    def split_sections(self, payload: Dict[str, Any] | None) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
        if not isinstance(payload, dict):
            return {}, {}, {}
        meta = payload.get("_meta") if isinstance(payload.get("_meta"), dict) else {}
        style_fields = meta.get("style") if isinstance(meta.get("style"), dict) else {}
        script_settings = meta.get("script") if isinstance(meta.get("script"), dict) else {}
        effect_meta = meta.get("effects") if isinstance(meta.get("effects"), dict) else {}
        structured_meta = meta.get("effects_structured") if isinstance(meta.get("effects_structured"), dict) else {}
        combined_effects = dict(effect_meta)
        if structured_meta:
            combined_effects.update(structured_meta)
        if style_fields and script_settings and (effect_meta or structured_meta):
            return style_fields, script_settings, combined_effects

        style_fields = self._normalise_style_fields(self._extract_style_fields(payload))
        script_settings = self._normalise_script_settings(self._extract_script_settings(payload))
        effect_overrides, effect_structured = self._normalise_effect_settings(self._extract_effect_settings(payload))
        combined = dict(effect_overrides)
        if effect_structured:
            combined.update(effect_structured)
        return style_fields, script_settings, combined

    @staticmethod
    def _normalise_key(value: str) -> str:
        return value.replace("-", "").replace("_", "").lower()

    def _extract_style_fields(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        extracted: Dict[str, Any] = {}
        for key, value in payload.items():
            alias = STYLE_KEY_ALIASES.get(self._normalise_key(str(key)))
            if alias:
                extracted[alias] = value
            elif str(key) in _STYLE_KEY_CANONICAL:
                extracted[str(key)] = value
        return extracted

    def _extract_script_settings(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        extracted: Dict[str, Any] = {}
        for key, value in payload.items():
            normalised = self._normalise_key(str(key))
            if normalised in _SCRIPT_KEY_CANONICAL:
                extracted[_SCRIPT_KEY_CANONICAL[normalised]] = value
            elif str(key) in _SCRIPT_KEY_CANONICAL.values():
                extracted[str(key)] = value
        return extracted

    def _extract_effect_settings(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        extracted: Dict[str, Any] = {}
        meta = payload.get("_meta") if isinstance(payload.get("_meta"), dict) else None
        if meta:
            structured_meta = meta.get("effects_structured")
            if isinstance(structured_meta, dict):
                for key, value in structured_meta.items():
                    extracted[key] = value
            effect_meta = meta.get("effects")
            if isinstance(effect_meta, dict):
                for key, value in effect_meta.items():
                    if key not in extracted:
                        extracted[key] = value
        for key, value in payload.items():
            normalised = self._normalise_key(str(key))
            if normalised in _EFFECT_KEY_CANONICAL:
                extracted[_EFFECT_KEY_CANONICAL[normalised]] = value
            elif str(key) in _EFFECT_KEY_CANONICAL.values():
                extracted[str(key)] = value
        return extracted

    def _normalise_style_fields(self, values: Dict[str, Any]) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for key, value in values.items():
            alias = STYLE_KEY_ALIASES.get(self._normalise_key(str(key)))
            if not alias:
                alias = _STYLE_KEY_CANONICAL.get(str(key), None)
            if not alias:
                continue
            coercer = getattr(self, f"_coerce_style_{alias.lower()}", self._coerce_style_default)
            coerced = coercer(alias, value)
            if coerced is not None:
                result[alias] = coerced
        return result

    def _normalise_script_settings(self, values: Dict[str, Any]) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for key, value in values.items():
            normalised = self._normalise_key(str(key))
            alias = _SCRIPT_KEY_CANONICAL.get(normalised)
            if not alias:
                continue
            coercer = getattr(self, f"_coerce_script_{alias.lower()}", self._coerce_script_default)
            coerced = coercer(alias, value)
            if coerced is not None:
                result[alias] = coerced
        return result

    def _normalise_effect_settings(self, values: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        result: Dict[str, Any] = {}
        structured: Dict[str, Any] = {}
        for key, value in values.items():
            normalised = self._normalise_key(str(key))
            alias = _EFFECT_KEY_CANONICAL.get(normalised)
            if not alias:
                continue
            coercer = getattr(self, f"_coerce_effect_{alias.lower()}", self._coerce_effect_default)
            coerced = coercer(alias, value)
            if isinstance(coerced, tuple) and len(coerced) == 2:
                override_value, structured_value = coerced
                if override_value is not None:
                    result[alias] = override_value
                if structured_value is not None:
                    structured[alias] = structured_value
            elif coerced is not None:
                result[alias] = coerced
        return result, structured

    def _coerce_style_default(self, key: str, value: Any) -> Any:
        if value is None:
            return None
        return str(value).strip()

    def _coerce_style_fontname(self, _key: str, value: Any) -> Any:
        if value is None:
            return None
        return str(value).strip()

    def _coerce_style_fontsize(self, _key: str, value: Any) -> Any:
        number = self._to_positive_float(value, minimum=1.0)
        return int(number) if number is not None else None

    def _coerce_style_primarycolour(self, _key: str, value: Any) -> Any:
        return self._coerce_colour(value)

    def _coerce_style_secondarycolour(self, _key: str, value: Any) -> Any:
        return self._coerce_colour(value)

    def _coerce_style_outlinecolour(self, _key: str, value: Any) -> Any:
        return self._coerce_colour(value)

    def _coerce_style_backcolour(self, _key: str, value: Any) -> Any:
        return self._coerce_colour(value)

    def _coerce_style_outline(self, _key: str, value: Any) -> Any:
        return self._to_non_negative_float(value)

    def _coerce_style_shadow(self, _key: str, value: Any) -> Any:
        return self._to_non_negative_float(value)

    def _coerce_style_alignment(self, _key: str, value: Any) -> Any:
        number = self._to_int(value)
        if number is None:
            return None
        number = max(1, min(9, number))
        return number

    def _coerce_style_marginl(self, _key: str, value: Any) -> Any:
        return self._to_non_negative_int(value)

    def _coerce_style_marginr(self, _key: str, value: Any) -> Any:
        return self._to_non_negative_int(value)

    def _coerce_style_marginv(self, _key: str, value: Any) -> Any:
        return self._to_non_negative_int(value)

    def _coerce_style_bold(self, _key: str, value: Any) -> Any:
        if isinstance(value, bool):
            return -1 if value else 0
        number = self._to_int(value)
        if number is None:
            return None
        return -1 if number not in {0, False} else 0

    def _coerce_style_italic(self, _key: str, value: Any) -> Any:
        if isinstance(value, bool):
            return -1 if value else 0
        number = self._to_int(value)
        if number is None:
            return None
        return -1 if number not in {0, False} else 0

    def _coerce_style_spacing(self, _key: str, value: Any) -> Any:
        return self._to_float(value)

    def _coerce_script_default(self, key: str, value: Any) -> Any:
        if key in {"PlayResX", "PlayResY", "WrapStyle"}:
            return self._to_positive_int(value)
        if key == "ScaledBorderAndShadow":
            return self._to_bool(value)
        if key in {"Title", "YCbCrMatrix"}:
            return str(value).strip() if value is not None else None
        return value

    def _coerce_script_playresx(self, key: str, value: Any) -> Any:
        return self._to_positive_int(value)

    def _coerce_script_playresy(self, key: str, value: Any) -> Any:
        return self._to_positive_int(value)

    def _coerce_script_wrapstyle(self, key: str, value: Any) -> Any:
        return self._to_positive_int(value)

    def _coerce_script_scaledborderandshadow(self, _key: str, value: Any) -> Any:
        return self._to_bool(value)

    def _coerce_script_title(self, _key: str, value: Any) -> Any:
        return str(value).strip() if value is not None else None

    def _coerce_script_ycbcrmatrix(self, _key: str, value: Any) -> Any:
        return str(value).strip() if value is not None else None

    def _coerce_effect_default(self, key: str, value: Any) -> Any:
        if value is None:
            return None
        return str(value).strip()

    def _coerce_effect_blur(self, _key: str, value: Any) -> Any:
        return self._to_non_negative_float(value)

    def _coerce_effect_animation(self, key: str, value: Any) -> Any:
        override, structured = self._normalise_animation_value(value)
        if override is None and structured is None:
            return None
        return override, structured

    def _coerce_effect_move(self, key: str, value: Any) -> Any:
        override, structured = self._normalise_move_value(value)
        if override is None and structured is None:
            return None
        return override, structured

    def _coerce_effect_fade(self, key: str, value: Any) -> Any:
        override, structured = self._normalise_fade_value(value)
        if override is None and structured is None:
            return None
        return override, structured

    def _coerce_effect_effect(self, key: str, value: Any) -> Any:
        return str(value).strip() if value is not None else None

    def _coerce_effect_textoverride(self, key: str, value: Any) -> Any:
        return self._format_override(value)

    def _coerce_effect_sequencemode(self, _key: str, value: Any) -> Any:
        if value is None:
            return None
        text = str(value).strip().lower()
        if not text:
            return None
        mapped = {
            "word": "word-continuous",
            "word-continuous": "word-continuous",
            "wordcontinuous": "word-continuous",
            "word_sequence": "word-continuous",
            "wordsequence": "word-continuous",
        }
        if text in {"none", "off", "false"}:
            return None
        return mapped.get(text, text)

    def _coerce_effect_sequencejitter(self, _key: str, value: Any) -> Any:
        if value is None:
            return None

        def _pair(dx: Any, dy: Any) -> Dict[str, float]:
            dx_value = self._to_non_negative_float(dx)
            dy_value = self._to_non_negative_float(dy)
            return {
                "dx": dx_value if dx_value is not None else 0.0,
                "dy": dy_value if dy_value is not None else 0.0,
            }

        if isinstance(value, dict):
            dx_raw = value.get("dx", value.get("x"))
            dy_raw = value.get("dy", value.get("y"))
            return _pair(dx_raw, dy_raw)

        if isinstance(value, (list, tuple)) and len(value) >= 2:
            return _pair(value[0], value[1])

        text = str(value).strip()
        if not text:
            return None
        parts = re.split(r"[\s,]+", text)
        if len(parts) >= 2:
            return _pair(parts[0], parts[1])

        number = self._to_non_negative_float(text)
        if number is None:
            return None
        return _pair(number, number)

    def _coerce_effect_alignmentvariant(self, _key: str, value: Any) -> Any:
        if value is None:
            return None
        text = str(value).strip().lower()
        if not text:
            return None
        if text in {"center-lower", "center_lower", "centre-lower", "centerlower"}:
            return "center-lower"
        return None

    def _coerce_effect_sequenceanchor(self, _key: str, value: Any) -> Any:
        if value is None:
            return None

        def _anchor(x_val: Any, y_val: Any) -> Dict[str, float] | None:
            x_num = self._to_positive_float(x_val, minimum=0.0)
            y_num = self._to_positive_float(y_val, minimum=0.0)
            if x_num is None or y_num is None:
                return None
            return {"x": x_num, "y": y_num}

        if isinstance(value, dict):
            return _anchor(value.get("x"), value.get("y"))

        if isinstance(value, (list, tuple)) and len(value) >= 2:
            return _anchor(value[0], value[1])

        text = str(value).strip()
        if not text:
            return None
        parts = re.split(r"[\s,]+", text)
        if len(parts) >= 2:
            return _anchor(parts[0], parts[1])
        return None

    def _coerce_effect_textcase(self, _key: str, value: Any) -> Any:
        if value is None:
            return None
        text = str(value).strip().lower()
        if not text or text in {"none", "normal", "default"}:
            return None
        if text in {"upper", "uppercase", "caps", "allupper", "allcaps"}:
            return "upper"
        if text in {"lower", "lowercase", "alllower"}:
            return "lower"
        return None

    def _coerce_effect_strippunctuation(self, _key: str, value: Any) -> Any:
        if value is None:
            return None
        return bool(self._to_bool(value))

    def _coerce_colour(self, value: Any) -> Any:
        if value is None:
            return None
        text = str(value).strip().upper()
        if not text:
            return None
        if text.startswith("#"):
            text = text[1:]
        if not text.startswith("&H"):
            if len(text) == 6:
                text = f"&H00{text}"
            elif len(text) == 8:
                text = f"&H{text}"
            else:
                raise ValueError("颜色格式需要 &H 后跟 6 或 8 位十六进制")
        if not _COLOR_PATTERN.match(text):
            raise ValueError("颜色格式需要 &H 后跟 6 或 8 位十六进制")
        if len(text) == 8:
            text = text[:2] + "00" + text[2:]
        return text

    def _format_override(self, value: Any) -> Any:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        if not text.startswith("\\") and not text.startswith("{"):
            text = "\\" + text.lstrip("\\")
        if text.startswith("\\"):
            text = "{" + text + "}"
        return text

    @staticmethod
    def _strip_braces(text: str) -> str:
        trimmed = text.strip()
        if trimmed.startswith("{") and trimmed.endswith("}"):
            return trimmed[1:-1].strip()
        return trimmed

    def _clean_override_text(self, text: str) -> str:
        stripped = self._strip_braces(str(text))
        if not stripped:
            return ""
        if not stripped.startswith("\\"):
            stripped = "\\" + stripped.lstrip("\\")
        return stripped

    def _format_float_value(self, value: float) -> str:
        if math.isfinite(value) and float(int(round(value))) == float(value):
            return str(int(round(value)))
        return ("%0.6f" % float(value)).rstrip("0").rstrip(".")

    def _extract_point(self, value: Any, *, label: str) -> Tuple[int, int]:
        if value is None:
            raise ValueError(f"{label} 需要提供坐标")
        if isinstance(value, dict):
            x_raw = value.get("x", value.get("X"))
            y_raw = value.get("y", value.get("Y"))
            x = self._to_int(x_raw)
            y = self._to_int(y_raw)
            if x is None or y is None:
                raise ValueError(f"{label} 坐标需要为整数")
            return x, y
        if isinstance(value, (list, tuple)) and len(value) >= 2:
            x = self._to_int(value[0])
            y = self._to_int(value[1])
            if x is None or y is None:
                raise ValueError(f"{label} 坐标需要为整数")
            return x, y
        if isinstance(value, str):
            parts = re.split(r"[\s,]+", value.strip())
            if len(parts) >= 2:
                x = self._to_int(parts[0])
                y = self._to_int(parts[1])
                if x is None or y is None:
                    raise ValueError(f"{label} 坐标需要为整数")
                return x, y
        raise ValueError(f"{label} 需要提供有效的坐标")

    def _normalise_move_value(self, value: Any) -> Tuple[str | None, Dict[str, Any] | None]:
        if value is None:
            return None, None
        if isinstance(value, (list, tuple)):
            config = self._normalise_move_sequence(value)
            override = self._format_move_override(config)
            return override, config
        if isinstance(value, dict):
            config = self._normalise_move_dict(value)
            override = self._format_move_override(config)
            return override, config
        text = str(value).strip()
        if not text:
            return None, None
        override = self._format_override(text)
        structured = self._parse_move_override(override)
        return override, structured

    def _normalise_move_sequence(self, value: Iterable[Any]) -> Dict[str, Any]:
        numbers: List[int] = []
        for item in value:
            number = self._to_int(item)
            if number is None:
                raise ValueError("Move 序列需要整数参数")
            numbers.append(number)
        if len(numbers) < 4:
            raise ValueError("Move 至少需要四个数值")
        from_point = {"x": numbers[0], "y": numbers[1]}
        to_point = {"x": numbers[2], "y": numbers[3]}
        config: Dict[str, Any] = {"from": from_point, "to": to_point}
        if len(numbers) >= 5:
            t1 = max(numbers[4], 0)
            config["t1"] = t1
            t2 = numbers[5] if len(numbers) >= 6 else t1
            config["t2"] = max(t2, t1)
        return config

    def _normalise_move_dict(self, value: Dict[str, Any]) -> Dict[str, Any]:
        from_source = value.get("from") or value.get("start")
        to_source = value.get("to") or value.get("end")
        from_point = self._extract_point(from_source, label="Move 起点")
        to_point = self._extract_point(to_source, label="Move 终点")
        config: Dict[str, Any] = {
            "from": {"x": int(from_point[0]), "y": int(from_point[1])},
            "to": {"x": int(to_point[0]), "y": int(to_point[1])},
        }
        t1_raw = value.get("t1") or value.get("start_time")
        t2_raw = value.get("t2") or value.get("end_time")
        if t1_raw is not None or t2_raw is not None:
            t1 = self._to_non_negative_int(t1_raw)
            t2 = self._to_non_negative_int(t2_raw if t2_raw is not None else t1_raw)
            if t1 is None:
                t1 = 0
            if t2 is None:
                t2 = t1
            t1 = max(t1, 0)
            t2 = max(t2, t1)
            config["t1"] = t1
            config["t2"] = t2
        return config

    def _format_move_override(self, config: Dict[str, Any]) -> str:
        from_point = config.get("from", {})
        to_point = config.get("to", {})
        x1 = int(from_point.get("x", 0))
        y1 = int(from_point.get("y", 0))
        x2 = int(to_point.get("x", 0))
        y2 = int(to_point.get("y", 0))
        override = f"\\move({x1},{y1},{x2},{y2}"
        t1 = config.get("t1")
        t2 = config.get("t2")
        if t1 is not None or t2 is not None:
            t1_val = max(self._to_non_negative_int(t1) or 0, 0)
            t2_val = self._to_non_negative_int(t2)
            if t2_val is None:
                t2_val = t1_val
            t2_val = max(t2_val, t1_val)
            override += f",{t1_val},{t2_val}"
        override += ")"
        return "{" + override + "}"

    def _parse_move_override(self, value: str) -> Dict[str, Any] | None:
        text = self._strip_braces(value)
        match = _MOVE_PATTERN.search(text)
        if not match:
            return None
        x1 = int(match.group(1))
        y1 = int(match.group(2))
        x2 = int(match.group(3))
        y2 = int(match.group(4))
        config: Dict[str, Any] = {
            "from": {"x": x1, "y": y1},
            "to": {"x": x2, "y": y2},
        }
        if match.group(5) is not None:
            t1 = max(int(match.group(5)), 0)
            t2_raw = match.group(6)
            t2 = max(int(t2_raw) if t2_raw is not None else t1, t1)
            config["t1"] = t1
            config["t2"] = t2
        return config

    def _normalise_fade_value(self, value: Any) -> Tuple[str | None, Dict[str, Any] | None]:
        if value is None:
            return None, None
        if isinstance(value, dict):
            config = self._normalise_fade_dict(value)
            if config is None:
                return None, None
            override = self._format_fade_override(config)
            return override, config
        text = str(value).strip()
        if not text:
            return None, None
        override = self._format_override(text)
        structured = self._parse_fade_override(override)
        return override, structured

    def _normalise_fade_dict(self, value: Dict[str, Any]) -> Dict[str, Any] | None:
        normalised_keys = {self._normalise_key(str(k)): k for k in value.keys()}
        mode_raw = value.get("mode")
        mode_text = str(mode_raw).strip().lower() if isinstance(mode_raw, str) else ""

        def _get(key: str) -> Any:
            original = normalised_keys.get(key)
            if original is None:
                return None
            return value.get(original)

        fade_in_raw = _get("fadin") or _get("fadein")
        fade_out_raw = _get("fadout") or _get("fadeout")
        if mode_text in {"fad", "simple"} or fade_in_raw is not None or fade_out_raw is not None:
            fade_in = self._to_non_negative_int(fade_in_raw)
            fade_out = self._to_non_negative_int(fade_out_raw)
            if fade_in is None and fade_out is None:
                return None
            fade_in = max(fade_in or 0, 0)
            fade_out = max(fade_out or 0, 0)
            return {"mode": "fad", "fadeIn": fade_in, "fadeOut": fade_out}

        alpha_from_raw = _get("alphafrom") or _get("alpha1")
        alpha_mid_raw = _get("alphamid") or _get("alpha2")
        alpha_to_raw = _get("alphato") or _get("alpha3")
        if mode_text in {"fade", "advanced"} or (
            alpha_from_raw is not None and alpha_mid_raw is not None and alpha_to_raw is not None
        ):
            alpha_from = self._clamp_alpha(alpha_from_raw)
            alpha_mid = self._clamp_alpha(alpha_mid_raw)
            alpha_to = self._clamp_alpha(alpha_to_raw)
            times: List[int] = []
            for key in ("t1", "t2", "t3", "t4"):
                time_value = self._to_non_negative_int(_get(key))
                if time_value is None:
                    raise ValueError("Fade 高级模式需要提供 t1~t4 数值")
                times.append(time_value)
            t1, t2, t3, t4 = times
            return {
                "mode": "fade",
                "alphaFrom": alpha_from,
                "alphaMid": alpha_mid,
                "alphaTo": alpha_to,
                "t1": t1,
                "t2": t2,
                "t3": t3,
                "t4": t4,
            }
        return None

    def _format_fade_override(self, config: Dict[str, Any]) -> str:
        mode = config.get("mode") or ("fade" if "alphaFrom" in config else "fad")
        if mode == "fade":
            alpha_from = self._clamp_alpha(config.get("alphaFrom"))
            alpha_mid = self._clamp_alpha(config.get("alphaMid"))
            alpha_to = self._clamp_alpha(config.get("alphaTo"))
            t1 = self._to_non_negative_int(config.get("t1")) or 0
            t2 = self._to_non_negative_int(config.get("t2")) or t1
            t3 = self._to_non_negative_int(config.get("t3")) or t2
            t4 = self._to_non_negative_int(config.get("t4")) or t3
            override = f"\\fade({alpha_from},{alpha_mid},{alpha_to},{t1},{t2},{t3},{t4})"
        else:
            fade_in = self._to_non_negative_int(config.get("fadeIn")) or 0
            fade_out = self._to_non_negative_int(config.get("fadeOut")) or 0
            override = f"\\fad({fade_in},{fade_out})"
        return "{" + override + "}"

    def _parse_fade_override(self, value: str) -> Dict[str, Any] | None:
        text = self._strip_braces(value)
        match_fad = _FAD_PATTERN.search(text)
        if match_fad:
            fade_in = int(match_fad.group(1))
            fade_out = int(match_fad.group(2))
            return {"mode": "fad", "fadeIn": fade_in, "fadeOut": fade_out}
        match_fade = _FADE_PATTERN.search(text)
        if match_fade:
            alpha_from = int(match_fade.group(1))
            alpha_mid = int(match_fade.group(2))
            alpha_to = int(match_fade.group(3))
            t1 = int(match_fade.group(4))
            t2 = int(match_fade.group(5))
            t3 = int(match_fade.group(6))
            t4 = int(match_fade.group(7))
            return {
                "mode": "fade",
                "alphaFrom": alpha_from,
                "alphaMid": alpha_mid,
                "alphaTo": alpha_to,
                "t1": t1,
                "t2": t2,
                "t3": t3,
                "t4": t4,
            }
        return None

    def _clamp_alpha(self, value: Any) -> int:
        number = self._to_non_negative_int(value)
        if number is None:
            raise ValueError("Alpha 需要为 0~255 的整数")
        return max(0, min(255, number))

    def _normalise_animation_value(self, value: Any) -> Tuple[str | None, Dict[str, Any] | None]:
        if value is None:
            return None, None
        if isinstance(value, dict):
            transforms_source = value.get("transforms")
            if not isinstance(transforms_source, (list, tuple)):
                return None, None
            transforms: List[Dict[str, Any]] = []
            for index, item in enumerate(transforms_source):
                if not isinstance(item, dict):
                    raise ValueError("Animation transforms 需要为对象数组")
                override_raw = item.get("override") or item.get("text") or item.get("tags")
                if not override_raw:
                    raise ValueError(f"Animation 第 {index + 1} 个变换缺少 override")
                override = self._clean_override_text(str(override_raw))
                if not override:
                    raise ValueError(f"Animation 第 {index + 1} 个变换缺少有效的 override")
                start_raw = item.get("start")
                end_raw = item.get("end")
                accel_raw = item.get("accel")
                start_val = self._to_non_negative_int(start_raw)
                end_val = self._to_non_negative_int(end_raw)
                if (start_raw is not None) != (end_raw is not None):
                    raise ValueError("Animation 需要同时提供 start 与 end 或者都不提供")
                accel_val = None
                if accel_raw is not None and accel_raw != "":
                    accel_val = self._to_float(accel_raw)
                    if accel_val is None or math.isnan(accel_val) or accel_val < 0:
                        raise ValueError("Animation accel 需要为非负数字")
                transform: Dict[str, Any] = {"override": override}
                if start_val is not None and end_val is not None:
                    start_val = max(start_val, 0)
                    end_val = max(end_val, start_val)
                    transform["start"] = start_val
                    transform["end"] = end_val
                if accel_val is not None:
                    transform["accel"] = accel_val
                transforms.append(transform)
            if not transforms:
                return None, None
            override = "{" + "".join(self._format_transform_override(entry) for entry in transforms) + "}"
            return override, {"transforms": transforms}
        text = str(value).strip()
        if not text:
            return None, None
        override = self._format_override(text)
        structured = self._parse_animation_override(override)
        return override, structured

    def _format_transform_override(self, transform: Dict[str, Any]) -> str:
        args: List[str] = []
        start = transform.get("start")
        end = transform.get("end")
        accel = transform.get("accel")
        if start is not None and end is not None:
            args.append(str(int(start)))
            args.append(str(int(end)))
            if accel is not None:
                args.append(self._format_float_value(float(accel)))
        elif accel is not None:
            # 若仅设置 accel，则默认 start/end 为 0
            args.append("0")
            args.append("0")
            args.append(self._format_float_value(float(accel)))
        override = transform.get("override")
        if not isinstance(override, str):
            raise ValueError("Animation override 需要为字符串")
        cleaned_override = self._clean_override_text(override)
        if not cleaned_override:
            raise ValueError("Animation override 需要为有效的标签")
        args.append(cleaned_override)
        return "\\t(" + ",".join(args) + ")"

    def _parse_animation_override(self, value: str) -> Dict[str, Any] | None:
        text = self._strip_braces(value)
        matches = list(_TRANSFORM_PATTERN.finditer(text))
        if not matches:
            return None
        transforms: List[Dict[str, Any]] = []
        for match in matches:
            content = match.group(1)
            parts = self._split_transform_args(content)
            if not parts:
                continue
            override_part = parts[-1]
            start_val = end_val = None
            accel_val = None
            numeric_parts = parts[:-1]
            if numeric_parts:
                start_val = self._to_non_negative_int(numeric_parts[0])
            if len(numeric_parts) >= 2:
                end_val = self._to_non_negative_int(numeric_parts[1])
            if len(numeric_parts) >= 3:
                accel_val = self._to_float(numeric_parts[2])
            transform: Dict[str, Any] = {"override": self._clean_override_text(override_part)}
            if start_val is not None and end_val is not None:
                transform["start"] = max(start_val, 0)
                transform["end"] = max(end_val, transform["start"])
            if accel_val is not None and not math.isnan(accel_val) and accel_val >= 0:
                transform["accel"] = accel_val
            transforms.append(transform)
        if not transforms:
            return None
        return {"transforms": transforms}

    def _split_transform_args(self, content: str) -> List[str]:
        args: List[str] = []
        current: List[str] = []
        depth = 0
        for char in content:
            if char == "," and depth == 0:
                arg = "".join(current).strip()
                args.append(arg)
                current = []
                continue
            if char in "({[":
                depth += 1
            elif char in ")}]" and depth > 0:
                depth -= 1
            current.append(char)
        if current:
            args.append("".join(current).strip())
        return args

    @staticmethod
    def _to_int(value: Any) -> int | None:
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _to_positive_int(value: Any) -> int | None:
        number = SubtitleStyleService._to_int(value)
        if number is None:
            return None
        return max(1, number)

    @staticmethod
    def _to_non_negative_int(value: Any) -> int | None:
        number = SubtitleStyleService._to_int(value)
        if number is None:
            return None
        return max(0, number)

    @staticmethod
    def _to_float(value: Any) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _to_positive_float(value: Any, *, minimum: float = 0.0) -> float | None:
        number = SubtitleStyleService._to_float(value)
        if number is None or math.isnan(number):
            return None
        return max(minimum, number)

    @staticmethod
    def _to_non_negative_float(value: Any) -> float | None:
        number = SubtitleStyleService._to_float(value)
        if number is None or math.isnan(number):
            return None
        return max(0.0, number)

    @staticmethod
    def _to_bool(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            return value.strip().lower() not in {"false", "0", "no"}
        return bool(value)

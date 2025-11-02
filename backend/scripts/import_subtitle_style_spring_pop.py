"""Import or update the 'Spring Pop Words' subtitle style."""
from __future__ import annotations

from datetime import datetime

from app.database import get_db_session
from app.models.subtitle_style import SubtitleStyle
from app.services.subtitle_style_service import SubtitleStyleService

STYLE_NAME = "Spring Pop Words"
STYLE_DESCRIPTION = "Q弹弹簧逐词显示样式，模仿 Spring Pop Words 示例。"
SAMPLE_TEXT = "Love is never gone away"

style_fields = {
    "Fontname": "Arial",
    "Fontsize": 80,
    "PrimaryColour": "&H00FFFFFF",
    "SecondaryColour": "&H000000FF",
    "OutlineColour": "&H00000000",
    "BackColour": "&H80000000",
    "Bold": True,
    "Italic": False,
    "ScaleX": 60,
    "ScaleY": 60,
    "Spacing": 0,
    "Outline": 4,
    "Shadow": 2,
    "Alignment": 2,
    "MarginL": 10,
    "MarginR": 10,
    "MarginV": 300,
}

script_settings = {
    "Title": "Spring Pop Words (1080x1920)",
    "PlayResX": 1080,
    "PlayResY": 1920,
    "WrapStyle": 1,
    "ScaledBorderAndShadow": True,
}

effect_settings = {
    "SequenceMode": "word-continuous",
    "SequenceJitter": {"dx": 3, "dy": 3},
    "AlignmentVariant": "center-lower",
    "Move": {
        "from": {"x": 540, "y": 1640},
        "to": {"x": 540, "y": 1550},
        "t1": 0,
        "t2": 240,
    },
    "Animation": {
        "transforms": [
            {"start": 0, "end": 220, "accel": 0.45, "override": "\\fscx120\\fscy120"},
            {"start": 220, "end": 420, "override": "\\fscx102\\fscy102\\bord6"},
            {"start": 420, "end": 680, "override": "\\bord4"},
        ]
    },
    "Fade": {"mode": "fad", "fadeIn": 80, "fadeOut": 120},
    "TextOverride": "\\alpha&H20&",
}


def main() -> None:
    service = SubtitleStyleService()
    config = service.normalise_payload(
        style_fields=style_fields,
        script_settings=script_settings,
        effect_settings=effect_settings,
    )

    db = get_db_session()
    try:
        existing = db.query(SubtitleStyle).filter(SubtitleStyle.name == STYLE_NAME).one_or_none()
        if existing:
            existing.description = STYLE_DESCRIPTION
            existing.sample_text = SAMPLE_TEXT
            existing.is_active = True
            existing.style_payload = config.payload
            existing.updated_at = datetime.utcnow()
            target = existing
            action = "updated"
        else:
            target = SubtitleStyle(
                name=STYLE_NAME,
                description=STYLE_DESCRIPTION,
                sample_text=SAMPLE_TEXT,
                is_active=True,
                is_default=False,
                style_payload=config.payload,
            )
            db.add(target)
            action = "created"

        db.commit()
        print(f"Subtitle style '{STYLE_NAME}' {action} successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    main()

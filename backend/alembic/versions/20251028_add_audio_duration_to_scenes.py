"""Add audio_duration column to scenes

Revision ID: 20251028_add_audio_duration_to_scenes
Revises: 20251027_add_gemini_prompt_tables
Create Date: 2025-10-28 00:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251028_add_audio_duration_to_scenes"
down_revision = "20251027_add_gemini_prompt_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("scenes")}
    if "audio_duration" not in columns:
        op.add_column(
            "scenes",
            sa.Column(
                "audio_duration",
                sa.Float(),
                nullable=True,
                comment="音频时长（秒）",
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("scenes")}
    if "audio_duration" in columns:
        op.drop_column("scenes", "audio_duration")

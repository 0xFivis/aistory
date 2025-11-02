"""Add selected Fish Audio voice per task.

Revision ID: 20251023_add_fishaudio_voice_selection
Revises: 20251022_add_scene_video_celery_id
Create Date: 2025-10-23 15:20:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251023_add_fishaudio_voice_selection"
down_revision = "20251022_add_scene_video_celery_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column("selected_voice_id", sa.String(length=128), nullable=True, comment="Fish Audio voice_id chosen for this task"),
    )
    op.add_column(
        "tasks",
        sa.Column("selected_voice_name", sa.String(length=128), nullable=True, comment="Display name of the selected voice"),
    )


def downgrade() -> None:
    op.drop_column("tasks", "selected_voice_name")
    op.drop_column("tasks", "selected_voice_id")

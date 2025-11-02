"""Add video_prompt column to scenes

Revision ID: add_video_prompt_to_scenes
Revises: d5f6a7b8c9d0
Create Date: 2025-10-18
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "add_video_prompt_to_scenes"
down_revision = "d5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "scenes",
        sa.Column("video_prompt", sa.Text(), nullable=True, comment="图生视频提示词"),
    )


def downgrade() -> None:
    op.drop_column("scenes", "video_prompt")

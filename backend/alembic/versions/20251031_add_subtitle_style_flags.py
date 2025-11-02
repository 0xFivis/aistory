"""add subtitle style default flag

Revision ID: 20251031_add_subtitle_style_flags
Revises: 20251031_create_subtitle_documents
Create Date: 2025-10-31
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251031_add_subtitle_style_flags"
down_revision = "20251031_create_subtitle_documents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "subtitle_styles",
        sa.Column(
            "is_default",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
            comment="是否为系统默认字幕样式",
        ),
    )
    op.execute("UPDATE subtitle_styles SET is_default = 0 WHERE is_default IS NULL")


def downgrade() -> None:
    op.drop_column("subtitle_styles", "is_default")

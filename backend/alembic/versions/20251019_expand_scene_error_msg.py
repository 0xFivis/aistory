"""Expand scenes.error_msg column to Text

Revision ID: 20251019_expand_scene_error_msg
Revises: 20241019_expand_error_msg
Create Date: 2025-10-19 11:45:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20251019_expand_scene_error_msg"
down_revision = "20241019_expand_error_msg"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("scenes", schema=None) as batch_op:
        batch_op.alter_column(
            "error_msg",
            type_=sa.Text(),
            existing_type=sa.String(length=255),
            existing_nullable=True,
            comment="错误信息",
        )


def downgrade() -> None:
    with op.batch_alter_table("scenes", schema=None) as batch_op:
        batch_op.alter_column(
            "error_msg",
            type_=sa.String(length=255),
            existing_type=sa.Text(),
            existing_nullable=True,
            comment="错误信息",
        )

"""Rename style_presets.model_id to checkpoint_id.

Revision ID: 20251019_rename_style_ckpt
Revises: 20251019_expand_scene_error_msg
Create Date: 2025-10-19 18:45:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251019_rename_style_ckpt"
down_revision = "20251019_expand_scene_error_msg"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("style_presets")}

    if "model_id" in columns:
        with op.batch_alter_table("style_presets", schema=None) as batch_op:
            batch_op.alter_column(
                "model_id",
                new_column_name="checkpoint_id",
                existing_type=sa.String(length=128),
                existing_nullable=True,
                existing_comment="主模型 ID",
                comment="主模型 Checkpoint ID",
            )
    elif "checkpoint_id" in columns:
        with op.batch_alter_table("style_presets", schema=None) as batch_op:
            batch_op.alter_column(
                "checkpoint_id",
                existing_type=sa.String(length=128),
                existing_nullable=True,
                existing_comment="主模型 Checkpoint ID",
                comment="主模型 Checkpoint ID",
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("style_presets")}

    if "checkpoint_id" in columns:
        with op.batch_alter_table("style_presets", schema=None) as batch_op:
            batch_op.alter_column(
                "checkpoint_id",
                new_column_name="model_id",
                existing_type=sa.String(length=128),
                existing_nullable=True,
                existing_comment="主模型 Checkpoint ID",
                comment="主模型 ID",
            )

"""Rename Liblib-specific columns to generic names.

Revision ID: rename_style_preset_columns
Revises: add_style_presets_table
Create Date: 2025-10-19
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "rename_style_preset_columns"
down_revision = "add_style_presets_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "style_presets",
        "liblib_lora_id",
        new_column_name="lora_id",
        existing_type=sa.String(length=128),
        existing_nullable=True,
        existing_comment="Liblib LoRA ID",
        comment="LoRA ID",
    )
    op.alter_column(
        "style_presets",
        "liblib_model_id",
        new_column_name="model_id",
        existing_type=sa.String(length=128),
        existing_nullable=True,
        existing_comment="Liblib 主模型 ID",
        comment="主模型 ID",
    )


def downgrade() -> None:
    op.alter_column(
        "style_presets",
        "lora_id",
        new_column_name="liblib_lora_id",
        existing_type=sa.String(length=128),
        existing_nullable=True,
        existing_comment="LoRA ID",
        comment="Liblib LoRA ID",
    )
    op.alter_column(
        "style_presets",
        "model_id",
        new_column_name="liblib_model_id",
        existing_type=sa.String(length=128),
        existing_nullable=True,
        existing_comment="主模型 ID",
        comment="Liblib 主模型 ID",
    )

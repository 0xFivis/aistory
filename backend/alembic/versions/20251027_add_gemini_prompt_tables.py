"""add gemini prompt templates tables

Revision ID: 20251027_add_gemini_prompt_tables
Revises: 20251026_create_runninghub_workflows
Create Date: 2025-10-27 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20251027_add_gemini_prompt_tables"
down_revision = "20251026_create_runninghub_workflows"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "gemini_prompt_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("slug", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("file_path", sa.String(length=255), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_gemini_prompt_templates_slug"),
        sa.UniqueConstraint("file_path", name="uq_gemini_prompt_templates_path"),
    )

    op.create_table(
        "gemini_prompt_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=True),
        sa.Column("response_text", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="success"),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["gemini_prompt_templates.id"],
            name="fk_gemini_prompt_records_template",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_gemini_prompt_templates_created_at",
        "gemini_prompt_templates",
        ["created_at"],
    )
    op.create_index(
        "ix_gemini_prompt_records_template_id",
        "gemini_prompt_records",
        ["template_id"],
    )
    op.create_index(
        "ix_gemini_prompt_records_created_at",
        "gemini_prompt_records",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_gemini_prompt_records_created_at", table_name="gemini_prompt_records")
    op.drop_index("ix_gemini_prompt_records_template_id", table_name="gemini_prompt_records")
    op.drop_table("gemini_prompt_records")
    op.drop_index("ix_gemini_prompt_templates_created_at", table_name="gemini_prompt_templates")
    op.drop_table("gemini_prompt_templates")

"""add service concurrency tables

Revision ID: 20251025_add_service_concurrency
Revises: 20251023_add_fishaudio_voice_selection
Create Date: 2025-10-25 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20251025_add_service_concurrency"
down_revision = "20251023_add_fishaudio_voice_selection"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "service_concurrency_limits",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("service_name", sa.String(length=64), nullable=False),
        sa.Column("feature", sa.String(length=64), nullable=True),
        sa.Column("max_slots", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("wait_interval_seconds", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("wait_timeout_seconds", sa.Integer(), nullable=True),
        sa.Column("slot_timeout_seconds", sa.Integer(), nullable=False, server_default="600"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("1")),
    sa.Column("created_at", sa.DateTime(), nullable=True),
    sa.Column("updated_at", sa.DateTime(), nullable=True),
        mysql_COMMENT="外部服务并发额度配置",
    )
    op.create_index(
        "idx_service_feature",
        "service_concurrency_limits",
        ["service_name", "feature"],
        unique=True,
    )

    op.create_table(
        "service_concurrency_slots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("service_name", sa.String(length=64), nullable=False),
        sa.Column("feature", sa.String(length=64), nullable=True),
        sa.Column("resource_id", sa.String(length=191), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
    sa.Column("acquired_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("released_at", sa.DateTime(), nullable=True),
        sa.Column("meta_json", sa.JSON(), nullable=True),
    sa.Column("created_at", sa.DateTime(), nullable=True),
    sa.Column("updated_at", sa.DateTime(), nullable=True),
        mysql_COMMENT="服务并发占用记录",
    )
    op.create_index(
        "idx_service_status",
        "service_concurrency_slots",
        ["service_name", "feature", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_service_status", table_name="service_concurrency_slots")
    op.drop_table("service_concurrency_slots")
    op.drop_index("idx_service_feature", table_name="service_concurrency_limits")
    op.drop_table("service_concurrency_limits")

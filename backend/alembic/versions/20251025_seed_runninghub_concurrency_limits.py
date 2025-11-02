"""seed runninghub concurrency limits

Revision ID: 20251025_seed_runninghub_concurrency_limits
Revises: 20251025_add_service_concurrency
Create Date: 2025-10-25 12:00:00
"""
from __future__ import annotations

from datetime import datetime

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20251025_seed_runninghub_concurrency_limits"
down_revision = "20251025_add_service_concurrency"
branch_labels = None
depends_on = None

limits_table = sa.table(
    "service_concurrency_limits",
    sa.column("service_name", sa.String(length=64)),
    sa.column("feature", sa.String(length=64)),
    sa.column("max_slots", sa.Integer()),
    sa.column("wait_interval_seconds", sa.Integer()),
    sa.column("wait_timeout_seconds", sa.Integer()),
    sa.column("slot_timeout_seconds", sa.Integer()),
    sa.column("enabled", sa.Boolean()),
    sa.column("created_at", sa.DateTime()),
    sa.column("updated_at", sa.DateTime()),
)

RUNNINGHUB_LIMITS = (
    {
        "service_name": "runninghub",
        "feature": "image",
        "max_slots": 3,
        "wait_interval_seconds": 5,
        "wait_timeout_seconds": 120,
        "slot_timeout_seconds": 900,
        "enabled": True,
    },
    {
        "service_name": "runninghub",
        "feature": "video",
        "max_slots": 3,
        "wait_interval_seconds": 8,
        "wait_timeout_seconds": 180,
        "slot_timeout_seconds": 1200,
        "enabled": True,
    },
)


def upgrade() -> None:
    bind = op.get_bind()
    now = datetime.utcnow()

    for entry in RUNNINGHUB_LIMITS:
        feature = entry["feature"]
        service = entry["service_name"]

        exists = bind.execute(
            sa.select(sa.literal(1))
            .select_from(limits_table)
            .where(limits_table.c.service_name == service)
            .where(limits_table.c.feature == feature)
            .limit(1)
        ).first()

        if exists:
            bind.execute(
                sa.update(limits_table)
                .where(limits_table.c.service_name == service)
                .where(limits_table.c.feature == feature)
                .values(
                    max_slots=entry["max_slots"],
                    wait_interval_seconds=entry["wait_interval_seconds"],
                    wait_timeout_seconds=entry["wait_timeout_seconds"],
                    slot_timeout_seconds=entry["slot_timeout_seconds"],
                    enabled=entry["enabled"],
                    updated_at=now,
                )
            )
        else:
            to_insert = dict(entry)
            to_insert.update({"created_at": now, "updated_at": now})
            bind.execute(sa.insert(limits_table).values(**to_insert))


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.delete(limits_table).where(limits_table.c.service_name == "runninghub")
    )

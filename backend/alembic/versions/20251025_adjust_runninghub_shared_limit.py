"""use shared runninghub service-level limit

Revision ID: 20251025_adjust_runninghub_shared_limit
Revises: 20251025_seed_runninghub_concurrency_limits
Create Date: 2025-10-25 14:30:00
"""
from __future__ import annotations

from datetime import datetime

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20251025_adjust_runninghub_shared_limit"
down_revision = "20251025_seed_runninghub_concurrency_limits"
branch_labels = None
depends_on = None

limits_table = sa.table(
    "service_concurrency_limits",
    sa.column("id", sa.Integer()),
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

FEATURE_LIMITS = [
    ("runninghub", "image"),
    ("runninghub", "video"),
]

SERVICE_LEVEL_LIMIT = {
    "service_name": "runninghub",
    "feature": None,
    "max_slots": 3,
    "wait_interval_seconds": 5,
    "wait_timeout_seconds": 180,
    "slot_timeout_seconds": 900,
    "enabled": True,
}


def upgrade() -> None:
    bind = op.get_bind()

    # Remove feature-scoped limits so slots are shared
    for service, feature in FEATURE_LIMITS:
        bind.execute(
            sa.delete(limits_table)
            .where(limits_table.c.service_name == service)
            .where(limits_table.c.feature == feature)
        )

    now = datetime.utcnow()

    existing = bind.execute(
        sa.select(limits_table.c.id)
        .where(limits_table.c.service_name == SERVICE_LEVEL_LIMIT["service_name"])
        .where(limits_table.c.feature == SERVICE_LEVEL_LIMIT["feature"])
        .limit(1)
    ).first()

    payload = dict(SERVICE_LEVEL_LIMIT)
    payload.update({"updated_at": now})

    if existing:
        bind.execute(
            sa.update(limits_table)
            .where(limits_table.c.id == existing.id)
            .values(**payload)
        )
    else:
        payload.update({"created_at": now})
        bind.execute(sa.insert(limits_table).values(**payload))


def downgrade() -> None:
    bind = op.get_bind()

    # Remove shared service-level limit
    bind.execute(
        sa.delete(limits_table)
        .where(limits_table.c.service_name == SERVICE_LEVEL_LIMIT["service_name"])
        .where(limits_table.c.feature == SERVICE_LEVEL_LIMIT["feature"])
    )

    now = datetime.utcnow()

    # Recreate feature-scoped limits as they existed before
    feature_values = [
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
    ]

    for entry in feature_values:
        entry.update({"created_at": now, "updated_at": now})
        bind.execute(sa.insert(limits_table).values(**entry))

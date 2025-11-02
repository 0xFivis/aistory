"""Merge heads: service_credential_unique + add_image_celery_id

Revision ID: 20251022_merge_heads_credential_and_image_celery
Revises: 20251021_service_credential_unique, 20251022_add_image_celery_id
Create Date: 2025-10-22 09:00:00.000000

"""
from __future__ import annotations

from alembic import op


# revision identifiers, used by Alembic.
revision = "20251022_merge_heads_credential_and_image_celery"
down_revision = (
    "20251021_service_credential_unique",
    "20251022_add_image_celery_id",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Merge migration: no-op.

This revision merges two independent heads into a single linear history so
`alembic upgrade head` can proceed. It intentionally performs no schema
changes — the child revisions have already made the intended changes.
"""
    pass


def downgrade() -> None:
    """Downgrade is a no-op for the merge node."""
    pass

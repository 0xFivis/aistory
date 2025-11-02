"""Legacy placeholder after renaming scene index migration.

Revision ID: 20251020_seq_idx_legacy
Revises: 20251020_scene_task_seq_idx
Create Date: 2025-10-20 10:15:00.000000

"""

from __future__ import annotations

from alembic import op


# revision identifiers, used by Alembic.
revision = "20251020_seq_idx_legacy"
down_revision = "20251020_scene_task_seq_idx"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """No-op: superseded by 20251020_scene_task_seq_idx."""
    # Index already created in the renamed migration.
    pass


def downgrade() -> None:
    """No-op: superseded by 20251020_scene_task_seq_idx."""
    pass

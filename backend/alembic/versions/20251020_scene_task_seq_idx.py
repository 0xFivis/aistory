"""Add composite index for scene ordering and pagination.

Revision ID: 20251020_scene_task_seq_idx
Revises: 20251019_scene_merge_split
Create Date: 2025-10-20 10:15:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251020_scene_task_seq_idx"
down_revision = "20251019_scene_merge_split"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add (task_id, seq) btree index to accelerate ordered lookups."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_indexes = {idx["name"] for idx in inspector.get_indexes("scenes")}

    if "idx_scenes_task_id_seq" not in existing_indexes:
        op.create_index(
            "idx_scenes_task_id_seq",
            "scenes",
            ["task_id", "seq"],
            unique=False,
        )


def downgrade() -> None:
    """Drop the composite index if present."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_indexes = {idx["name"] for idx in inspector.get_indexes("scenes")}

    if "idx_scenes_task_id_seq" in existing_indexes:
        op.drop_index("idx_scenes_task_id_seq", table_name="scenes")

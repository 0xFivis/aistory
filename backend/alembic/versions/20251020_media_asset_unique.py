"""Add unique constraint for media asset names per type.

Revision ID: 20251020_media_asset_unique
Revises: 20251020_seq_idx_legacy
Create Date: 2025-10-20 14:05:00.000000

"""

from __future__ import annotations

from alembic import op


# revision identifiers, used by Alembic.
revision = "20251020_media_asset_unique"
down_revision = "20251020_seq_idx_legacy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_media_asset_type_name",
        "media_assets",
        ["asset_type", "asset_name"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_media_asset_type_name", "media_assets", type_="unique")

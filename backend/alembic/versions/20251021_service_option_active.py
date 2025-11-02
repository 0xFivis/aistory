"""Add is_active flag to service options.

Revision ID: 20251021_service_option_active
Revises: 20251020_media_asset_unique
Create Date: 2025-10-21 08:00:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251021_service_option_active"
down_revision = "20251020_media_asset_unique"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add the is_active column with default True for existing rows."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("service_options")}

    if "is_active" not in columns:
        op.add_column(
            "service_options",
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        )
        # Remove the implicit server default now that existing rows are populated
        op.alter_column("service_options", "is_active", server_default=None)


def downgrade() -> None:
    """Drop the is_active column when rolling back."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("service_options")}

    if "is_active" in columns:
        op.drop_column("service_options", "is_active")

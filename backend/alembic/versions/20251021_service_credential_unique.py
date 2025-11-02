"""Enforce unique credentials per service and type.

Revision ID: 20251021_service_credential_unique
Revises: 20251021_service_option_active
Create Date: 2025-10-21 09:00:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251021_service_credential_unique"
down_revision = "20251021_service_option_active"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add unique constraint for (service_name, credential_type, credential_key)."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    constraints = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("service_credentials")
    }

    if "uq_service_credential_key" not in constraints:
        op.create_unique_constraint(
            "uq_service_credential_key",
            "service_credentials",
            ["service_name", "credential_type", "credential_key"],
        )


def downgrade() -> None:
    """Drop the unique constraint when rolling back."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    constraints = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("service_credentials")
    }

    if "uq_service_credential_key" in constraints:
        op.drop_constraint("uq_service_credential_key", "service_credentials", type_="unique")

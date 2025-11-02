"""
Add image_celery_id column to scenes table

Revision ID: 20251022_add_image_celery_id
Revises: 20251021_service_option_active
Create Date: 2025-10-22 00:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251022_add_image_celery_id"
down_revision = "20251021_service_option_active"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {c['name'] for c in inspector.get_columns('scenes')}
    if 'image_celery_id' not in columns:
        op.add_column(
            'scenes',
            sa.Column('image_celery_id', sa.String(length=128), nullable=True, comment='本地 Celery task id (用于 revoke/terminate)')
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {c['name'] for c in inspector.get_columns('scenes')}
    if 'image_celery_id' in columns:
        op.drop_column('scenes', 'image_celery_id')

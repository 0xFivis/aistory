"""add last_used_at to service_credentials

Revision ID: add_service_credential_last_used_at
Revises: 
Create Date: 2025-10-22
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251022_add_service_credential_last_used_at'
down_revision = '20251022_merge_heads_credential_and_image_celery'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('service_credentials', sa.Column('last_used_at', sa.DateTime(), nullable=True, comment='最后一次被分配使用的 UTC 时间'))


def downgrade():
    op.drop_column('service_credentials', 'last_used_at')

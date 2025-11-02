"""add task mode column

Revision ID: c4d5e6f7a8b9
Revises: b2c3d4e5f6g7
Create Date: 2025-10-17 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c4d5e6f7a8b9'
down_revision = 'b2c3d4e5f6g7'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('tasks', sa.Column('mode', sa.String(length=16), nullable=False, server_default='auto', comment='任务执行模式：auto/manual'))
    # Remove server_default if desired after data migration


def downgrade():
    op.drop_column('tasks', 'mode')

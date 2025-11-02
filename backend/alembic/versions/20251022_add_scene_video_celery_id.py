"""add video_celery_id to scenes

Revision ID: 20251022_add_scene_video_celery_id
Revises: 20251022_merge_heads_credential_and_image_celery
Create Date: 2025-10-22
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251022_add_scene_video_celery_id'
down_revision = '20251022_add_service_credential_last_used_at'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('scenes', sa.Column('video_celery_id', sa.String(128), nullable=True, comment='本地 Celery task id for video generation (用于 revoke/terminate)'))


def downgrade():
    op.drop_column('scenes', 'video_celery_id')

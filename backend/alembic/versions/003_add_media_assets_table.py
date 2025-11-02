"""Add media assets table

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2025-10-17 21:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6g7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    # 创建媒体素材表
    op.create_table(
        'media_assets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('asset_type', sa.String(20), nullable=False, comment='素材类型: bgm, image, video, template'),
        sa.Column('asset_name', sa.String(100), nullable=False, comment='素材名称'),
        sa.Column('file_url', sa.String(500), nullable=False, comment='文件URL'),
        sa.Column('file_path', sa.String(500), nullable=True, comment='本地文件路径'),
        sa.Column('duration', sa.Float(), nullable=True, comment='音频/视频时长（秒）'),
        sa.Column('file_size', sa.BigInteger(), nullable=True, comment='文件大小（字节）'),
        sa.Column('tags', sa.JSON(), nullable=True, comment='标签数组'),
        sa.Column('description', sa.Text(), nullable=True, comment='描述'),
        sa.Column('is_default', sa.Boolean(), nullable=False, default=False, comment='是否默认'),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True, comment='是否启用'),
        sa.Column('meta_info', sa.JSON(), nullable=True, comment='额外元数据（封面、波形等）'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_asset_type', 'asset_type', 'is_active'),
        comment='媒体素材表'
    )


def downgrade():
    op.drop_table('media_assets')

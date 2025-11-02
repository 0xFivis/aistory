"""Add service management tables

Revision ID: a1b2c3d4e5f6
Revises: 349a1a8ebac7
Create Date: 2025-10-17 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '349a1a8ebac7'
branch_labels = None
depends_on = None


def upgrade():
    # 1. 创建服务凭证表
    op.create_table(
        'service_credentials',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('service_name', sa.String(50), nullable=False, comment='服务名称: gemini, fishaudio, nca, liblib, fal, cloudinary'),
        sa.Column('credential_type', sa.String(20), nullable=False, default='api_key', comment='凭证类型: api_key, access_secret'),
        sa.Column('credential_key', sa.String(255), nullable=True, comment='API Key 或 Access Key'),
        sa.Column('credential_secret', sa.Text(), nullable=True, comment='Secret Key (加密存储)'),
        sa.Column('api_url', sa.String(255), nullable=True, comment='API Base URL'),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True, comment='是否启用'),
        sa.Column('description', sa.String(255), nullable=True, comment='描述'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_service_active', 'service_name', 'is_active'),
        comment='服务凭证表'
    )
    
    # 2. 创建服务选项表（可选参数库）
    op.create_table(
        'service_options',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('service_name', sa.String(50), nullable=False, comment='服务名称'),
        sa.Column('option_type', sa.String(50), nullable=False, comment='选项类型: voice_id, lora_id, model_id, style_preset'),
        sa.Column('option_key', sa.String(100), nullable=False, comment='选项键'),
        sa.Column('option_value', sa.String(255), nullable=False, comment='选项值'),
        sa.Column('option_name', sa.String(100), nullable=True, comment='显示名称'),
        sa.Column('description', sa.Text(), nullable=True, comment='描述'),
        sa.Column('is_default', sa.Boolean(), nullable=False, default=False, comment='是否默认'),
        sa.Column('meta_data', sa.JSON(), nullable=True, comment='额外元数据'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_service_type', 'service_name', 'option_type'),
        sa.UniqueConstraint('service_name', 'option_type', 'option_key', name='uq_service_option'),
        comment='服务可选参数表'
    )
    
    # 3. 增强 tasks 表
    op.add_column('tasks', sa.Column('task_config', sa.JSON(), nullable=True, comment='任务完整配置JSON'))
    op.add_column('tasks', sa.Column('progress', sa.Integer(), nullable=False, default=0, comment='任务进度 0-100'))
    op.add_column('tasks', sa.Column('total_scenes', sa.Integer(), nullable=True, comment='总分镜数'))
    op.add_column('tasks', sa.Column('completed_scenes', sa.Integer(), nullable=False, default=0, comment='已完成分镜数'))
    
    # 4. 增强 task_steps 表
    op.add_column('task_steps', sa.Column('retry_count', sa.Integer(), nullable=False, default=0, comment='重试次数'))
    op.add_column('task_steps', sa.Column('max_retries', sa.Integer(), nullable=False, default=3, comment='最大重试次数'))
    op.add_column('task_steps', sa.Column('progress', sa.Integer(), nullable=False, default=0, comment='步骤进度 0-100'))
    
    # 5. 增强 scenes 表 - 添加子状态
    op.add_column('scenes', sa.Column('narration_text', sa.Text(), nullable=True, comment='旁白文本'))
    op.add_column('scenes', sa.Column('narration_word_count', sa.Integer(), nullable=True, comment='旁白字数'))
    op.add_column('scenes', sa.Column('image_prompt', sa.Text(), nullable=True, comment='图片提示词'))
    op.add_column('scenes', sa.Column('image_status', mysql.TINYINT(), nullable=False, default=0, comment='图片状态：0待处理,1处理中,2成功,3失败'))
    op.add_column('scenes', sa.Column('audio_status', mysql.TINYINT(), nullable=False, default=0, comment='音频状态：0待处理,1处理中,2成功,3失败'))
    op.add_column('scenes', sa.Column('video_status', mysql.TINYINT(), nullable=False, default=0, comment='视频状态：0待处理,1处理中,2成功,3失败'))
    op.add_column('scenes', sa.Column('image_retry_count', sa.Integer(), nullable=False, default=0, comment='图片重试次数'))
    op.add_column('scenes', sa.Column('audio_retry_count', sa.Integer(), nullable=False, default=0, comment='音频重试次数'))
    op.add_column('scenes', sa.Column('video_retry_count', sa.Integer(), nullable=False, default=0, comment='视频重试次数'))
    op.add_column('scenes', sa.Column('image_url', sa.String(500), nullable=True, comment='图片URL'))
    op.add_column('scenes', sa.Column('audio_url', sa.String(500), nullable=True, comment='音频URL'))
    op.add_column('scenes', sa.Column('video_url', sa.String(500), nullable=True, comment='视频URL'))
    
    # 6. 增强 files 表
    op.add_column('files', sa.Column('duration', sa.Float(), nullable=True, comment='媒体时长（秒）'))
    op.add_column('files', sa.Column('width', sa.Integer(), nullable=True, comment='宽度（像素）'))
    op.add_column('files', sa.Column('height', sa.Integer(), nullable=True, comment='高度（像素）'))
    op.add_column('files', sa.Column('storage_type', sa.String(20), nullable=False, default='local', comment='存储类型: local, cloudinary, s3'))


def downgrade():
    # 删除新增的列
    op.drop_column('files', 'storage_type')
    op.drop_column('files', 'height')
    op.drop_column('files', 'width')
    op.drop_column('files', 'duration')
    
    op.drop_column('scenes', 'video_url')
    op.drop_column('scenes', 'audio_url')
    op.drop_column('scenes', 'image_url')
    op.drop_column('scenes', 'video_retry_count')
    op.drop_column('scenes', 'audio_retry_count')
    op.drop_column('scenes', 'image_retry_count')
    op.drop_column('scenes', 'video_status')
    op.drop_column('scenes', 'audio_status')
    op.drop_column('scenes', 'image_status')
    op.drop_column('scenes', 'image_prompt')
    op.drop_column('scenes', 'narration_word_count')
    op.drop_column('scenes', 'narration_text')
    
    op.drop_column('task_steps', 'progress')
    op.drop_column('task_steps', 'max_retries')
    op.drop_column('task_steps', 'retry_count')
    
    op.drop_column('tasks', 'completed_scenes')
    op.drop_column('tasks', 'total_scenes')
    op.drop_column('tasks', 'progress')
    op.drop_column('tasks', 'task_config')
    
    # 删除新建的表
    op.drop_table('service_options')
    op.drop_table('service_credentials')

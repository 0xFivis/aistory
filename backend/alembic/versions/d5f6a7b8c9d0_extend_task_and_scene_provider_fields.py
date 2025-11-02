"""Extend task, step, scene provider tracking

Revision ID: d5f6a7b8c9d0
Revises: c4d5e6f7a8b9
Create Date: 2025-10-18 09:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd5f6a7b8c9d0'
down_revision = 'c4d5e6f7a8b9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # tasks.providers
    op.add_column('tasks', sa.Column('providers', sa.JSON(), nullable=True, comment='功能模块选用的服务提供商映射，例如 {"image": "runninghub"}'))

    # task_steps additions
    op.add_column('task_steps', sa.Column('provider', sa.String(length=64), nullable=True, comment='本步骤使用的服务提供商'))
    op.add_column('task_steps', sa.Column('external_task_id', sa.String(length=128), nullable=True, comment='外部服务返回的任务ID或Job ID'))
    op.add_column('task_steps', sa.Column('context', sa.JSON(), nullable=True, comment='步骤运行时上下文信息，例如排队状态、回调信息'))

    # scenes additions
    op.add_column('scenes', sa.Column('image_provider', sa.String(length=64), nullable=True, comment='图片生成服务提供商'))
    op.add_column('scenes', sa.Column('audio_provider', sa.String(length=64), nullable=True, comment='音频生成服务提供商'))
    op.add_column('scenes', sa.Column('video_provider', sa.String(length=64), nullable=True, comment='视频生成或合成服务提供商'))
    op.add_column('scenes', sa.Column('image_job_id', sa.String(length=128), nullable=True, comment='图片生成外部任务ID'))
    op.add_column('scenes', sa.Column('audio_job_id', sa.String(length=128), nullable=True, comment='音频生成外部任务ID'))
    op.add_column('scenes', sa.Column('video_job_id', sa.String(length=128), nullable=True, comment='视频生成或合成外部任务ID'))
    op.add_column('scenes', sa.Column('image_meta', sa.JSON(), nullable=True, comment='图片生成的额外元数据，例如提示词、耗时'))
    op.add_column('scenes', sa.Column('audio_meta', sa.JSON(), nullable=True, comment='音频生成的额外元数据，例如音色、采样率'))
    op.add_column('scenes', sa.Column('video_meta', sa.JSON(), nullable=True, comment='视频生成/合成的额外元数据，例如分辨率、帧率'))

    # files additions
    op.add_column('files', sa.Column('provider', sa.String(length=64), nullable=True, comment='生成该文件的服务提供商'))
    op.add_column('files', sa.Column('origin_step', sa.String(length=64), nullable=True, comment='生成该文件的流程步骤标识'))


def downgrade() -> None:
    op.drop_column('files', 'origin_step')
    op.drop_column('files', 'provider')

    op.drop_column('scenes', 'video_meta')
    op.drop_column('scenes', 'audio_meta')
    op.drop_column('scenes', 'image_meta')
    op.drop_column('scenes', 'video_job_id')
    op.drop_column('scenes', 'audio_job_id')
    op.drop_column('scenes', 'image_job_id')
    op.drop_column('scenes', 'video_provider')
    op.drop_column('scenes', 'audio_provider')
    op.drop_column('scenes', 'image_provider')

    op.drop_column('task_steps', 'context')
    op.drop_column('task_steps', 'external_task_id')
    op.drop_column('task_steps', 'provider')

    op.drop_column('tasks', 'providers')

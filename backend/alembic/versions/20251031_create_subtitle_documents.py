"""create subtitle documents table

Revision ID: 20251031_create_subtitle_documents
Revises: 20251031_create_subtitle_styles
Create Date: 2025-10-31
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251031_create_subtitle_documents"
down_revision = "20251031_create_subtitle_styles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "subtitle_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
            server_onupdate=sa.func.now(),
        ),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, comment="关联任务 ID"),
        sa.Column("language", sa.String(length=16), nullable=True, comment="字幕语言代码"),
        sa.Column("model_name", sa.String(length=128), nullable=True, comment="识别模型名称"),
        sa.Column("text", sa.Text(), nullable=True, comment="完整字幕文本"),
        sa.Column("segments", sa.JSON(), nullable=False, comment="字幕片段 JSON 数据数组"),
        sa.Column("info", sa.JSON(), nullable=True, comment="识别附加信息"),
        sa.Column("options", sa.JSON(), nullable=True, comment="识别参数配置"),
    sa.Column("segment_count", sa.Integer(), nullable=False, server_default=sa.text("0"), comment="字幕片段数量"),
        sa.Column("srt_api_path", sa.String(length=512), nullable=True, comment="SRT 文件 API 路径"),
        sa.Column("srt_relative_path", sa.String(length=512), nullable=True, comment="SRT 文件相对路径"),
        sa.Column("srt_public_url", sa.String(length=512), nullable=True, comment="SRT 文件对外 URL"),
        sa.Column("ass_api_path", sa.String(length=512), nullable=True, comment="ASS 文件 API 路径"),
        sa.Column("ass_relative_path", sa.String(length=512), nullable=True, comment="ASS 文件相对路径"),
        sa.Column("ass_public_url", sa.String(length=512), nullable=True, comment="ASS 文件对外 URL"),
        sa.UniqueConstraint("task_id", name="uq_subtitle_documents_task_id"),
    )
    op.create_index("ix_subtitle_documents_task_id", "subtitle_documents", ["task_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_subtitle_documents_task_id", table_name="subtitle_documents")
    op.drop_table("subtitle_documents")

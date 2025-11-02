"""Split video generation and scene AV merge steps.

Revision ID: 20251019_scene_merge_split
Revises: 20251019_rename_style_ckpt
Create Date: 2025-10-19 19:40:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251019_scene_merge_split"
down_revision = "20251019_rename_style_ckpt"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("scenes", schema=None) as batch_op:
        batch_op.alter_column(
            "video_url",
            new_column_name="merge_video_url",
            existing_type=sa.String(length=500),
            existing_nullable=True,
            existing_comment="视频URL",
            comment="音视频合成后视频URL",
        )
        batch_op.add_column(
            sa.Column(
                "merge_status",
                sa.SmallInteger(),
                nullable=False,
                server_default="0",
                comment="音视频合成状态：0待处理,1处理中,2成功,3失败",
            )
        )
        batch_op.add_column(
            sa.Column(
                "merge_retry_count",
                sa.Integer(),
                nullable=False,
                server_default="0",
                comment="音视频合成重试次数",
            )
        )
        batch_op.add_column(
            sa.Column(
                "merge_video_provider",
                sa.String(length=64),
                nullable=True,
                comment="音视频合成服务提供商",
            )
        )
        batch_op.add_column(
            sa.Column(
                "merge_job_id",
                sa.String(length=128),
                nullable=True,
                comment="音视频合成外部任务ID",
            )
        )
        batch_op.add_column(
            sa.Column(
                "merge_meta",
                sa.JSON(),
                nullable=True,
                comment="音视频合成元数据",
            )
        )

    op.execute(
        "UPDATE scenes SET merge_status = CASE WHEN merge_video_url IS NOT NULL THEN 2 ELSE 0 END"
    )
    op.execute("UPDATE scenes SET merge_retry_count = 0 WHERE merge_retry_count IS NULL")

    with op.batch_alter_table("scenes", schema=None) as batch_op:
        batch_op.alter_column("merge_status", server_default=None)
        batch_op.alter_column("merge_retry_count", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("scenes", schema=None) as batch_op:
        batch_op.drop_column("merge_meta")
        batch_op.drop_column("merge_job_id")
        batch_op.drop_column("merge_video_provider")
        batch_op.drop_column("merge_retry_count")
        batch_op.drop_column("merge_status")
        batch_op.alter_column(
            "merge_video_url",
            new_column_name="video_url",
            existing_type=sa.String(length=500),
            existing_nullable=True,
            existing_comment="音视频合成后视频URL",
            comment="视频URL",
        )

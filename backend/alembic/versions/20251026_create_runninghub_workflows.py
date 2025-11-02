"""create runninghub workflow configuration table

Revision ID: 20251026_create_runninghub_workflows
Revises: 20251025_seed_runninghub_concurrency_limits
Create Date: 2025-10-26 10:00:00
"""
from __future__ import annotations

from datetime import datetime

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20251026_create_runninghub_workflows"
down_revision = "20251025_adjust_runninghub_shared_limit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "runninghub_workflows",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=True, unique=True),
        sa.Column("workflow_type", sa.String(length=32), nullable=False),
        sa.Column("workflow_id", sa.String(length=64), nullable=False),
        sa.Column("instance_type", sa.String(length=32), nullable=False, server_default="plus"),
        sa.Column("node_info_template", sa.JSON(), nullable=True),
        sa.Column("defaults", sa.JSON(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workflow_type", "name", name="uq_runninghub_workflow_name"),
    )

    op.create_index(
        "idx_runninghub_workflow_type",
        "runninghub_workflows",
        ["workflow_type", "is_active"],
    )

    op.add_column("style_presets", sa.Column("image_provider", sa.String(length=32), nullable=True))
    op.add_column("style_presets", sa.Column("video_provider", sa.String(length=32), nullable=True))
    op.add_column("style_presets", sa.Column("runninghub_image_workflow_id", sa.Integer(), nullable=True))
    op.add_column("style_presets", sa.Column("runninghub_video_workflow_id", sa.Integer(), nullable=True))

    op.create_foreign_key(
        "fk_style_presets_runninghub_image",
        "style_presets",
        "runninghub_workflows",
        ["runninghub_image_workflow_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_style_presets_runninghub_video",
        "style_presets",
        "runninghub_workflows",
        ["runninghub_video_workflow_id"],
        ["id"],
        ondelete="SET NULL",
    )

    workflows_table = sa.table(
        "runninghub_workflows",
        sa.column("name", sa.String),
        sa.column("slug", sa.String),
        sa.column("workflow_type", sa.String),
        sa.column("workflow_id", sa.String),
        sa.column("instance_type", sa.String),
        sa.column("node_info_template", sa.JSON),
        sa.column("defaults", sa.JSON),
        sa.column("description", sa.Text),
        sa.column("is_active", sa.Boolean),
        sa.column("is_default", sa.Boolean),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
    )

    now = datetime.utcnow()

    op.bulk_insert(
        workflows_table,
        [
            {
                "name": "默认图片工作流",
                "slug": "image.default",
                "workflow_type": "image",
                "workflow_id": "1978319996189302785",
                "instance_type": "plus",
                "node_info_template": [
                    {"nodeId": "6", "fieldName": "text", "fieldValue": "{{prompt}}"},
                    {"nodeId": "5", "fieldName": "width", "fieldValue": "{{width}}"},
                    {"nodeId": "5", "fieldName": "height", "fieldValue": "{{height}}"},
                ],
                "defaults": {
                    "width": 864,
                    "height": 1536,
                    "poll_attempts": 6,
                    "poll_interval": 60.0,
                    "initial_delay": 60.0,
                    "busy_wait": 10.0,
                    "create_attempts": 3,
                },
                "description": "默认 RunningHub 图生图工作流",
                "is_active": True,
                "is_default": True,
                "created_at": now,
                "updated_at": now,
            },
            {
                "name": "默认视频工作流",
                "slug": "video.default",
                "workflow_type": "video",
                "workflow_id": "1950150331004010497",
                "instance_type": "plus",
                "node_info_template": [
                    {"nodeId": "113", "fieldName": "select", "fieldValue": "{{node_113}}"},
                    {"nodeId": "153", "fieldName": "select", "fieldValue": "{{node_153}}"},
                    {"nodeId": "247", "fieldName": "select", "fieldValue": "{{node_247}}"},
                    {"nodeId": "272", "fieldName": "index", "fieldValue": "{{node_272}}"},
                    {"nodeId": "107", "fieldName": "value", "fieldValue": "{{duration}}"},
                    {"nodeId": "135", "fieldName": "image", "fieldValue": "{{image_url}}"},
                    {"nodeId": "116", "fieldName": "text", "fieldValue": "{{prompt}}"},
                ],
                "defaults": {
                    "node_113": 2,
                    "node_153": 2,
                    "node_247": 4,
                    "node_272": 2,
                    "poll_attempts": 6,
                    "poll_interval": 60.0,
                    "initial_delay": 60.0,
                    "busy_wait": 10.0,
                    "create_attempts": 3,
                    "min_duration": 2,
                    "max_duration": 8,
                },
                "description": "默认 RunningHub 图生视频工作流",
                "is_active": True,
                "is_default": True,
                "created_at": now,
                "updated_at": now,
            },
        ],
    )

    # 清理旧的 service_options 配置（workflow_config）
    op.execute(
        sa.text(
            "DELETE FROM service_options WHERE service_name = 'runninghub' AND option_type = 'workflow_config'"
        )
    )


def downgrade() -> None:
    op.execute("DELETE FROM service_options WHERE service_name = 'runninghub' AND option_type = 'workflow_config'")

    op.drop_constraint("fk_style_presets_runninghub_image", "style_presets", type_="foreignkey")
    op.drop_constraint("fk_style_presets_runninghub_video", "style_presets", type_="foreignkey")

    op.drop_column("style_presets", "runninghub_video_workflow_id")
    op.drop_column("style_presets", "runninghub_image_workflow_id")
    op.drop_column("style_presets", "video_provider")
    op.drop_column("style_presets", "image_provider")

    op.drop_index("idx_runninghub_workflow_type", table_name="runninghub_workflows")
    op.drop_table("runninghub_workflows")

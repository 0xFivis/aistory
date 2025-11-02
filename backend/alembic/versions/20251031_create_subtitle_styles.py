"""create subtitle styles table and task links

Revision ID: 20251031_create_subtitle_styles
Revises: 20251028_add_audio_duration_to_scenes
Create Date: 2025-10-31
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251031_create_subtitle_styles"
down_revision = "20251028_add_audio_duration_to_scenes"
branch_labels = None
depends_on = None


def _has_table(inspector, table_name: str) -> bool:
    try:
        return table_name in inspector.get_table_names()
    except Exception:
        return False


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_table(inspector, "subtitle_styles"):
        op.create_table(
            "subtitle_styles",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
                server_onupdate=sa.func.now(),
            ),
            sa.Column("name", sa.String(length=128), nullable=False, unique=True, comment="字幕样式名称"),
            sa.Column("description", sa.Text(), nullable=True, comment="字幕样式描述"),
            sa.Column("style_payload", sa.JSON(), nullable=False, comment="ASS/SSA 样式配置 JSON"),
            sa.Column("sample_text", sa.Text(), nullable=True, comment="示例文本或预览说明"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1"), comment="是否启用"),
        )

    task_columns = {col["name"] for col in inspector.get_columns("tasks")}
    if "subtitle_style_id" not in task_columns:
        op.add_column(
            "tasks",
            sa.Column(
                "subtitle_style_id",
                sa.Integer(),
                nullable=True,
                comment="选择的字幕样式 ID",
            ),
        )
    if "subtitle_style_snapshot" not in task_columns:
        op.add_column(
            "tasks",
            sa.Column(
                "subtitle_style_snapshot",
                sa.JSON(),
                nullable=True,
                comment="字幕样式快照 JSON",
            ),
        )

    existing_fks = {fk["name"] for fk in inspector.get_foreign_keys("tasks")}
    if "fk_tasks_subtitle_style_id" not in existing_fks:
        op.create_foreign_key(
            "fk_tasks_subtitle_style_id",
            source_table="tasks",
            referent_table="subtitle_styles",
            local_cols=["subtitle_style_id"],
            remote_cols=["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    existing_fks = {fk["name"] for fk in inspector.get_foreign_keys("tasks")}
    if "fk_tasks_subtitle_style_id" in existing_fks:
        op.drop_constraint("fk_tasks_subtitle_style_id", "tasks", type_="foreignkey")

    task_columns = {col["name"] for col in inspector.get_columns("tasks")}
    if "subtitle_style_snapshot" in task_columns:
        op.drop_column("tasks", "subtitle_style_snapshot")
    if "subtitle_style_id" in task_columns:
        op.drop_column("tasks", "subtitle_style_id")

    if _has_table(inspector, "subtitle_styles"):
        op.drop_table("subtitle_styles")

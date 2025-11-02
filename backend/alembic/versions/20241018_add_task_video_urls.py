"""Add merged/final video URL columns on tasks

Revision ID: add_task_video_urls
Revises: add_scene_raw_video_url
Create Date: 2025-10-18
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "add_task_video_urls"
down_revision = "add_scene_raw_video_url"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column("merged_video_url", sa.String(length=500), nullable=True, comment="分镜拼接后视频URL（未加背景音乐）"),
    )
    op.add_column(
        "tasks",
        sa.Column("final_video_url", sa.String(length=500), nullable=True, comment="最终成片URL（完成配乐/滤镜等处理）"),
    )

    connection = op.get_bind()
    tasks_table = sa.table(
        "tasks",
        sa.column("id", sa.Integer),
        sa.column("result", sa.JSON),
        sa.column("merged_video_url", sa.String(length=500)),
        sa.column("final_video_url", sa.String(length=500)),
    )

    select_stmt = sa.select(tasks_table.c.id, tasks_table.c.result)
    result = connection.execute(select_stmt)

    for row in result:
        result_json = row.result if hasattr(row, "result") else None
        if not isinstance(result_json, dict):
            continue

        updates = {}
        merged_url = result_json.get("merged_video_url")
        final_url = result_json.get("final_video_url")
        if merged_url:
            updates["merged_video_url"] = str(merged_url)
        if final_url:
            updates["final_video_url"] = str(final_url)

        if updates:
            update_stmt = (
                sa.update(tasks_table)
                .where(tasks_table.c.id == row.id)
                .values(**updates)
            )
            connection.execute(update_stmt)

    result.close()


def downgrade() -> None:
    op.drop_column("tasks", "final_video_url")
    op.drop_column("tasks", "merged_video_url")

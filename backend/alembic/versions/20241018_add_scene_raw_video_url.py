"""Add raw_video_url column to scenes

Revision ID: add_scene_raw_video_url
Revises: add_video_prompt_to_scenes
Create Date: 2025-10-18
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "add_scene_raw_video_url"
down_revision = "add_video_prompt_to_scenes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "scenes",
        sa.Column("raw_video_url", sa.String(length=500), nullable=True, comment="原始视频URL（未合成音频）"),
    )

    connection = op.get_bind()
    scenes_table = sa.table(
        "scenes",
        sa.column("id", sa.Integer),
        sa.column("raw_video_url", sa.String(length=500)),
        sa.column("video_meta", sa.JSON),
    )

    select_stmt = sa.select(scenes_table.c.id, scenes_table.c.video_meta)
    result = connection.execute(select_stmt)

    for row in result:
        video_meta = row.video_meta if hasattr(row, "video_meta") else None
        if isinstance(video_meta, dict):
            raw_url = video_meta.get("raw_video_url")
            if raw_url:
                update_stmt = (
                    sa.update(scenes_table)
                    .where(scenes_table.c.id == row.id)
                    .values(raw_video_url=str(raw_url))
                )
                connection.execute(update_stmt)

    result.close()


def downgrade() -> None:
    op.drop_column("scenes", "raw_video_url")

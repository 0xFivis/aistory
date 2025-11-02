"""Remove style_hint and style_keywords from style_presets

Revision ID: 20241019_remove_style_fields
Revises: 20241019_rename_style_preset_columns
Create Date: 2025-10-19 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20241019_remove_style_fields"
down_revision = "rename_style_preset_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("style_presets", schema=None) as batch_op:
        batch_op.drop_column("style_hint")
        batch_op.drop_column("style_keywords")


def downgrade() -> None:
    with op.batch_alter_table("style_presets", schema=None) as batch_op:
        batch_op.add_column(sa.Column("style_keywords", sa.JSON(), nullable=True, comment="风格关键词列表"))
        batch_op.add_column(sa.Column("style_hint", sa.Text(), nullable=True, comment="视觉风格提示或说明"))

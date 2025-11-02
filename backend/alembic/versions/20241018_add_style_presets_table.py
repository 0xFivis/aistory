"""Create style_presets table

Revision ID: add_style_presets_table
Revises: add_video_prompt_to_scenes
Create Date: 2025-10-18
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "add_style_presets_table"
down_revision = "add_task_video_urls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "style_presets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("name", sa.String(length=128), nullable=False, comment="风格名称"),
        sa.Column("description", sa.Text(), nullable=True, comment="风格说明"),
        sa.Column("prompt_example", sa.Text(), nullable=True, comment="提示词结构示例"),
        sa.Column("trigger_words", sa.Text(), nullable=True, comment="提示词触发词或前缀"),
        sa.Column("style_hint", sa.Text(), nullable=True, comment="视觉风格提示或说明"),
        sa.Column("style_keywords", sa.JSON(), nullable=True, comment="风格关键词列表"),
        sa.Column("word_count_strategy", sa.Text(), nullable=True, comment="旁白字数策略"),
        sa.Column("channel_identity", sa.Text(), nullable=True, comment="频道身份描述"),
        sa.Column("liblib_lora_id", sa.String(length=128), nullable=True, comment="Liblib LoRA ID"),
        sa.Column("liblib_model_id", sa.String(length=128), nullable=True, comment="Liblib 主模型 ID"),
        sa.Column("meta", sa.JSON(), nullable=True, comment="额外配置元数据"),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
            comment="是否启用",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_style_presets_name", "style_presets", ["name"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_style_presets_name", table_name="style_presets")
    op.drop_table("style_presets")

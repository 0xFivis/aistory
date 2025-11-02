from sqlalchemy import Column, String, Text, Boolean, JSON, Integer, ForeignKey

from .base import BaseModel


class StylePreset(BaseModel):
    __tablename__ = "style_presets"

    name = Column(String(128), nullable=False, unique=True, comment="风格名称")
    description = Column(Text, nullable=True, comment="风格说明")
    prompt_example = Column(Text, nullable=True, comment="提示词结构示例")
    trigger_words = Column(Text, nullable=True, comment="提示词触发词或前缀")
    word_count_strategy = Column(Text, nullable=True, comment="旁白字数策略")
    channel_identity = Column(Text, nullable=True, comment="频道身份描述")
    lora_id = Column(String(128), nullable=True, comment="LoRA ID")
    checkpoint_id = Column(String(128), nullable=True, comment="主模型 Checkpoint ID")
    image_provider = Column(String(32), nullable=True, comment="图片生成默认平台")
    video_provider = Column(String(32), nullable=True, comment="视频生成默认平台")
    runninghub_image_workflow_id = Column(
        Integer,
        ForeignKey("runninghub_workflows.id", ondelete="SET NULL"),
        nullable=True,
        comment="Runninghub 图片工作流 ID",
    )
    runninghub_video_workflow_id = Column(
        Integer,
        ForeignKey("runninghub_workflows.id", ondelete="SET NULL"),
        nullable=True,
        comment="Runninghub 视频工作流 ID",
    )
    meta = Column(JSON, nullable=True, comment="额外配置元数据")
    is_active = Column(Boolean, nullable=False, default=True, comment="是否启用")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "prompt_example": self.prompt_example,
            "trigger_words": self.trigger_words,
            "word_count_strategy": self.word_count_strategy,
            "channel_identity": self.channel_identity,
            "lora_id": self.lora_id,
            "checkpoint_id": self.checkpoint_id,
            "image_provider": self.image_provider,
            "video_provider": self.video_provider,
            "runninghub_image_workflow_id": self.runninghub_image_workflow_id,
            "runninghub_video_workflow_id": self.runninghub_video_workflow_id,
            "meta": self.meta,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

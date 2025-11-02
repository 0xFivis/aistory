from sqlalchemy import Column, String, Text, Boolean, JSON

from .base import BaseModel


class SubtitleStyle(BaseModel):
    __tablename__ = "subtitle_styles"

    name = Column(String(128), nullable=False, unique=True, comment="字幕样式名称")
    description = Column(Text, nullable=True, comment="字幕样式描述")
    style_payload = Column(JSON, nullable=False, comment="ASS/SSA 样式配置 JSON")
    sample_text = Column(Text, nullable=True, comment="示例文本或预览说明")
    is_active = Column(Boolean, nullable=False, default=True, comment="是否启用")
    is_default = Column(Boolean, nullable=False, default=False, comment="是否为系统默认字幕样式")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "style_payload": self.style_payload,
            "sample_text": self.sample_text,
            "is_active": self.is_active,
            "is_default": self.is_default,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

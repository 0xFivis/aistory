from sqlalchemy import Column, Integer, ForeignKey, String, Text, JSON, UniqueConstraint

from .base import BaseModel


class SubtitleDocument(BaseModel):
    __tablename__ = "subtitle_documents"
    __table_args__ = (
        UniqueConstraint("task_id", name="uq_subtitle_documents_task_id"),
    )

    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, comment="关联任务 ID")
    language = Column(String(16), nullable=True, comment="字幕语言代码")
    model_name = Column(String(128), nullable=True, comment="识别模型名称")
    text = Column(Text, nullable=True, comment="完整字幕文本")
    segments = Column(JSON, nullable=False, comment="字幕片段 JSON 数据数组")
    info = Column(JSON, nullable=True, comment="识别附加信息")
    options = Column(JSON, nullable=True, comment="识别参数配置")
    segment_count = Column(Integer, nullable=False, default=0, comment="字幕片段数量")

    srt_api_path = Column(String(512), nullable=True, comment="导出 SRT 文件 API 路径")
    srt_relative_path = Column(String(512), nullable=True, comment="导出 SRT 文件相对路径")
    srt_public_url = Column(String(512), nullable=True, comment="导出 SRT 文件对外 URL")

    ass_api_path = Column(String(512), nullable=True, comment="导出 ASS 文件 API 路径")
    ass_relative_path = Column(String(512), nullable=True, comment="导出 ASS 文件相对路径")
    ass_public_url = Column(String(512), nullable=True, comment="导出 ASS 文件对外 URL")

    def to_dict(self) -> dict:
        text = self.text or ""
        preview = text.strip()[:200]
        if not preview and isinstance(self.info, dict):
            preview_candidate = str(self.info.get("text_preview") or "").strip()
            if preview_candidate:
                preview = preview_candidate[:200]

        payload = {
            "id": self.id,
            "task_id": self.task_id,
            "language": self.language,
            "model_name": self.model_name,
            "text": text,
            "segments": self.segments,
            "segment_count": self.segment_count,
            "info": self.info,
            "options": self.options,
            "srt_api_path": self.srt_api_path,
            "srt_relative_path": self.srt_relative_path,
            "srt_public_url": self.srt_public_url,
            "ass_api_path": self.ass_api_path,
            "ass_relative_path": self.ass_relative_path,
            "ass_public_url": self.ass_public_url,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if preview:
            payload["text_preview"] = preview
        return payload

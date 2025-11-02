"""Models for Gemini prompt templates and execution records."""
from __future__ import annotations

from sqlalchemy import Boolean, Column, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from .base import BaseModel


class GeminiPromptTemplate(BaseModel):
    __tablename__ = "gemini_prompt_templates"

    name = Column(String(128), nullable=False)
    slug = Column(String(128), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    file_path = Column(String(255), nullable=False, unique=True)
    parameters = Column(JSON, nullable=False, default=list)
    is_active = Column(Boolean, nullable=False, default=True)

    records = relationship(
        "GeminiPromptRecord",
        back_populates="template",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "file_path": self.file_path,
            "parameters": list(self.parameters or []),
            "is_active": bool(self.is_active),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class GeminiPromptRecord(BaseModel):
    __tablename__ = "gemini_prompt_records"

    template_id = Column(
        Integer,
        ForeignKey("gemini_prompt_templates.id", ondelete="CASCADE"),
        nullable=False,
    )
    prompt = Column(Text, nullable=False)
    parameters = Column(JSON, nullable=True)
    response_text = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="success")
    latency_ms = Column(Integer, nullable=True)

    template = relationship("GeminiPromptTemplate", back_populates="records")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "template_id": self.template_id,
            "prompt": self.prompt,
            "parameters": self.parameters or {},
            "response_text": self.response_text,
            "error_message": self.error_message,
            "status": self.status,
            "latency_ms": self.latency_ms,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

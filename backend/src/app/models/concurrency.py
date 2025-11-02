"""数据库模型：服务并发限制与占用记录"""
from __future__ import annotations

from datetime import timedelta
from typing import Optional

from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON, Index

from .base import BaseModel
from app.utils.timezone import naive_now


class ServiceConcurrencyLimit(BaseModel):
    """存储服务/功能的并发额度配置。"""

    __tablename__ = "service_concurrency_limits"

    service_name = Column(String(64), nullable=False, comment="服务标识，例如 runninghub/liblib")
    feature = Column(String(64), nullable=True, comment="可选的功能标签，例如 image/video")
    max_slots = Column(Integer, nullable=False, default=0, comment="最大并发名额，<=0 表示禁用")
    wait_interval_seconds = Column(Integer, nullable=False, default=5, comment="满额后的轮询间隔 (秒)")
    wait_timeout_seconds = Column(Integer, nullable=True, comment="等待名额的最大时间 (秒)，为空则不限")
    slot_timeout_seconds = Column(Integer, nullable=False, default=600, comment="名额占用的超时时长 (秒)")
    enabled = Column(Boolean, nullable=False, default=True, comment="是否启用此限制")

    __table_args__ = (
        Index("idx_service_feature", "service_name", "feature", unique=True),
        {"comment": "外部服务并发额度配置"},
    )

    def slot_timeout(self) -> timedelta:
        seconds = self.slot_timeout_seconds or 600
        return timedelta(seconds=max(1, seconds))

    def wait_interval(self) -> float:
        return float(max(1, self.wait_interval_seconds or 1))


class ServiceConcurrencySlot(BaseModel):
    """记录正在占用的服务名额。"""

    __tablename__ = "service_concurrency_slots"

    STATUS_ACTIVE = "active"
    STATUS_RELEASED = "released"
    STATUS_ERROR = "error"
    STATUS_TIMEOUT = "timeout"
    STATUS_EXPIRED = "expired"

    service_name = Column(String(64), nullable=False, comment="服务标识")
    feature = Column(String(64), nullable=True, comment="功能标签")
    resource_id = Column(String(191), nullable=True, comment="业务资源标识，例如 task-scene")
    status = Column(String(32), nullable=False, default=STATUS_ACTIVE, comment="占用状态")
    acquired_at = Column(DateTime, nullable=False, default=naive_now, comment="占用时间")
    expires_at = Column(DateTime, nullable=True, comment="超时时刻")
    released_at = Column(DateTime, nullable=True, comment="释放时间")
    meta_json = Column(JSON, nullable=True, comment="附加信息，例如外部 job_id")

    __table_args__ = (
        Index("idx_service_status", "service_name", "feature", "status"),
        {"comment": "服务并发占用记录"},
    )

    def mark_released(self, status: str = STATUS_RELEASED, *, metadata: Optional[dict] = None) -> None:
        self.status = status
        self.released_at = naive_now()
        if metadata:
            existing = self.meta_json if isinstance(self.meta_json, dict) else {}
            existing.update(metadata)
            self.meta_json = existing


__all__ = ["ServiceConcurrencyLimit", "ServiceConcurrencySlot"]

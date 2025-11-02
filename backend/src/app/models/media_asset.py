"""媒体素材模型"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import Column, Integer, String, Text, Boolean, Float, BigInteger, DateTime, JSON, Index, UniqueConstraint
from .base import BaseModel


class MediaAsset(BaseModel):
    """媒体素材表 - 存储背景音乐、图片等可复用素材"""
    __tablename__ = "media_assets"
    
    asset_type = Column(String(20), nullable=False, comment="素材类型: bgm, image, video, template")
    asset_name = Column(String(100), nullable=False, comment="素材名称")
    file_url = Column(String(500), nullable=False, comment="文件URL")
    file_path = Column(String(500), nullable=True, comment="本地文件路径")
    duration = Column(Float, nullable=True, comment="音频/视频时长（秒）")
    file_size = Column(BigInteger, nullable=True, comment="文件大小（字节）")
    tags = Column(JSON, nullable=True, comment="标签数组")
    description = Column(Text, nullable=True, comment="描述")
    is_default = Column(Boolean, nullable=False, default=False, comment="是否默认")
    is_active = Column(Boolean, nullable=False, default=True, comment="是否启用")
    meta_info = Column(JSON, nullable=True, comment="额外元数据（封面、波形等）")
    
    __table_args__ = (
        Index('idx_asset_type', 'asset_type', 'is_active'),
        UniqueConstraint('asset_type', 'asset_name', name='uq_media_asset_type_name'),
        {'comment': '媒体素材表'}
    )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "asset_type": self.asset_type,
            "asset_name": self.asset_name,
            "file_url": self.file_url,
            "file_path": self.file_path,
            "duration": self.duration,
            "file_size": self.file_size,
            "tags": self.tags,
            "description": self.description,
            "is_default": self.is_default,
            "is_active": self.is_active,
            "meta_info": self.meta_info,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

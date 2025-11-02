"""服务凭证和配置管理模型"""
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON, Index, UniqueConstraint
from .base import BaseModel


class ServiceCredential(BaseModel):
    """服务凭证表 - 存储各服务的 API Keys"""
    __tablename__ = "service_credentials"
    
    service_name = Column(String(50), nullable=False, comment="服务名称: gemini, fishaudio, nca, liblib, fal, cloudinary")
    credential_type = Column(String(20), nullable=False, default="api_key", comment="凭证类型: api_key, access_secret")
    credential_key = Column(String(255), nullable=True, comment="API Key 或 Access Key")
    credential_secret = Column(Text, nullable=True, comment="Secret Key (加密存储)")
    api_url = Column(String(255), nullable=True, comment="API Base URL")
    is_active = Column(Boolean, nullable=False, default=True, comment="是否启用")
    last_used_at = Column(DateTime, nullable=True, comment="最后一次被分配使用的 UTC 时间")
    description = Column(String(255), nullable=True, comment="描述")
    
    __table_args__ = (
        Index('idx_service_active', 'service_name', 'is_active'),
        UniqueConstraint('service_name', 'credential_type', 'credential_key', name='uq_service_credential_key'),
        {'comment': '服务凭证表'}
    )
    
    def to_dict(self, include_secret: bool = False) -> Dict[str, Any]:
        """转换为字典，默认不包含敏感信息"""
        data = {
            "id": self.id,
            "service_name": self.service_name,
            "credential_type": self.credential_type,
            "credential_key": self.credential_key[:10] + "..." if self.credential_key and not include_secret else self.credential_key,
            "api_url": self.api_url,
            "is_active": self.is_active,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_used_at": self.last_used_at.isoformat() if getattr(self, 'last_used_at', None) else None,
        }
        if include_secret:
            data["credential_secret"] = self.credential_secret
        return data


class ServiceOption(BaseModel):
    """服务可选参数表 - 存储可供任务选择的配置项"""
    __tablename__ = "service_options"
    
    service_name = Column(String(50), nullable=False, comment="服务名称")
    option_type = Column(String(50), nullable=False, comment="选项类型: voice_id, lora_id, model_id, style_preset")
    option_key = Column(String(100), nullable=False, comment="选项键")
    option_value = Column(String(255), nullable=False, comment="选项值")
    option_name = Column(String(100), nullable=True, comment="显示名称")
    description = Column(Text, nullable=True, comment="描述")
    is_default = Column(Boolean, nullable=False, default=False, comment="是否默认")
    is_active = Column(Boolean, nullable=False, default=True, comment="是否可用")
    meta_data = Column(JSON, nullable=True, comment="额外元数据")
    
    __table_args__ = (
        Index('idx_service_type', 'service_name', 'option_type'),
        UniqueConstraint('service_name', 'option_type', 'option_key', name='uq_service_option'),
        {'comment': '服务可选参数表'}
    )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "service_name": self.service_name,
            "option_type": self.option_type,
            "option_key": self.option_key,
            "option_value": self.option_value,
            "option_name": self.option_name,
            "description": self.description,
            "is_default": self.is_default,
            "is_active": self.is_active,
            "meta_data": self.meta_data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

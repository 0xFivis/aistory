"""Fish Audio TTS 服务"""
import logging
import time
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.core.http_client import create_http_client
from app.models.service_config import ServiceCredential, ServiceOption
from .base import BaseService
from .exceptions import (
    APIException,
    ConfigurationException,
    ValidationException,
)


class FishAudioService(BaseService):
    """Fish Audio TTS 服务类"""
    
    def __init__(self, db: Session, voice_id: Optional[str] = None):
        """
        初始化 Fish Audio 服务
        
        Args:
            db: 数据库会话
            voice_id: 音色ID（可选，如果不提供则使用默认音色）
        """
        super().__init__()
        self.db = db
        self._load_credentials()
        self._load_voice_config(voice_id)
        self.client = create_http_client("fishaudio", timeout=60)
        # Validate after loading credentials
        self._validate_configuration()
    
    @property
    def service_name(self) -> str:
        return "Fish Audio"
    
    def _validate_configuration(self) -> None:
        """验证配置是否完整"""
        if not self.api_key:
            raise ConfigurationException(
                "Fish Audio API Key not configured",
                service_name=self.service_name
            )
        if not self.api_url:
            raise ConfigurationException(
                "Fish Audio API URL not configured",
                service_name=self.service_name
            )
    
    def _load_credentials(self):
        """从数据库加载凭证"""
        credential = self.db.query(ServiceCredential).filter(
            ServiceCredential.service_name == "fishaudio",
            ServiceCredential.is_active == True
        ).first()
        
        if not credential:
            raise ConfigurationException(
                "Fish Audio credentials not found in database",
                service_name=self.service_name
            )
        
        self.api_key = credential.credential_key
        if not credential.api_url:
            raise ConfigurationException(
                "Fish Audio API URL not configured in database",
                service_name=self.service_name,
            )
        raw_url = credential.api_url.rstrip("/")
        # 官方文档的示例常带有 /v1，统一去掉版本后缀以避免重复拼接
        self.api_url = raw_url.removesuffix("/v1")
        self.logger.info("Loaded Fish Audio credentials from database (api_url=%s)", self.api_url)
    
    def _load_voice_config(self, voice_id: Optional[str] = None):
        """从数据库加载音色配置
        
        Args:
            voice_id: 指定的音色ID，如果为None则使用默认音色
        """
        if voice_id:
            # 使用指定的音色ID
            option = self.db.query(ServiceOption).filter(
                ServiceOption.service_name == "fishaudio",
                ServiceOption.option_type == "voice_id",
                ServiceOption.option_key == voice_id
            ).first()
            
            if not option:
                self.logger.warning(f"Voice ID '{voice_id}' not found in database, will try to use it directly")
                self.voice_id = voice_id
                self.voice_name = voice_id
            else:
                self.voice_id = option.option_value
                self.voice_name = option.option_name
        else:
            # 使用默认音色
            option = self.db.query(ServiceOption).filter(
                ServiceOption.service_name == "fishaudio",
                ServiceOption.option_type == "voice_id",
                ServiceOption.is_default == True
            ).first()
            
            if not option:
                    raise ConfigurationException(
                        "No default Fish Audio voice configured",
                        service_name=self.service_name
                    )
            
            self.voice_id = option.option_value
            self.voice_name = option.option_name
        
        self.logger.info(f"Using Fish Audio voice: {self.voice_name} ({self.voice_id})")
    
    def text_to_speech(
        self,
        text: str,
        voice_id: Optional[str] = None,
        format: str = "mp3",
        sample_rate: int = 44100,
    ) -> bytes:
        """
        将文本转换为语音
        
        Args:
            text: 要转换的文本
            voice_id: 音色ID（可选，不提供则使用初始化时的音色）
            format: 音频格式 (mp3/wav/flac)
            sample_rate: 采样率
        
        Returns:
            音频文件的二进制数据
        
        Raises:
            ValidationException: 输入验证失败
            APIException: API调用失败
        """
        # 验证输入
        if not text or not text.strip():
            raise ValidationException("text cannot be empty", field="text")
        
        if len(text) > 5000:
            raise ValidationException(
                "text too long (max 5000 characters)",
                field="text"
            )
        
        # 使用指定音色或默认音色
        target_voice_id = voice_id or self.voice_id
        
        # 构建请求
        url = f"{self.api_url}/v1/tts"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "text": text,
            "reference_id": target_voice_id,
            "format": format,
            "sample_rate": sample_rate,
            "normalize": True,
            "mp3_bitrate": 192
        }
        
        try:
            self._log_request("text_to_speech", method="POST", text_length=len(text))

            start_time = time.time()
            response = self.client.post(url, json=payload, headers=headers)
            duration_ms = (time.time() - start_time) * 1000

            if response.status_code == 200:
                self._log_response("text_to_speech", status_code=200, duration_ms=duration_ms)
                return response.content
            else:
                error_msg = f"Fish Audio API error: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", error_msg)
                except:
                    error_msg = response.text or error_msg
                
                self._log_error(error_msg, {"endpoint": "text_to_speech"})
                raise APIException(
                    message=error_msg,
                    service_name=self.service_name,
                    status_code=response.status_code,
                    response_data=error_data if 'error_data' in locals() else None,
                )
        
        except APIException:
            raise
        except Exception as e:
            self._log_error(e, {"endpoint": "text_to_speech"})
            raise APIException(
                message=f"Failed to call Fish Audio API: {str(e)}",
                service_name=self.service_name,
            )
    
    def get_available_voices(self) -> list:
        """
        获取数据库中配置的所有可用音色
        
        Returns:
            音色列表
        """
        voices = self.db.query(ServiceOption).filter(
            ServiceOption.service_name == "fishaudio",
            ServiceOption.option_type == "voice_id"
        ).all()
        
        return [
            {
                "key": v.option_key,
                "id": v.option_value,
                "name": v.option_name,
                "description": v.description,
                "is_default": v.is_default
            }
            for v in voices
        ]
    
    def close(self):
        """关闭客户端连接"""
        if hasattr(self, 'client'):
            self.client.close()

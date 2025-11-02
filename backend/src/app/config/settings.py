from functools import lru_cache
import os
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[3]
ENV_FILE_PATH = BASE_DIR / ".env"

class Settings(BaseSettings):
    # Database settings
    DATABASE_URL: str = Field(..., env="DATABASE_URL")

    # Application settings
    APP_NAME: Optional[str] = Field(None, env="APP_NAME")
    APP_VERSION: Optional[str] = Field(None, env="APP_VERSION")
    DEBUG: Optional[bool] = Field(None, env="DEBUG")
    LOG_LEVEL: Optional[str] = Field(None, env="LOG_LEVEL")

    # FastAPI settings
    API_HOST: Optional[str] = Field(None, env="API_HOST")
    API_PORT: Optional[int] = Field(None, env="API_PORT")
    APP_TIMEZONE: Optional[str] = Field(None, env="APP_TIMEZONE")
    CORS_ALLOW_ORIGINS: Optional[str] = Field(None, env="CORS_ALLOW_ORIGINS")

    # Celery & Redis settings
    REDIS_URL: Optional[str] = Field(None, env="REDIS_URL")
    CELERY_BROKER_URL: Optional[str] = Field(None, env="CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND: Optional[str] = Field(None, env="CELERY_RESULT_BACKEND")
    # Celery connection retry policy
    CELERY_BROKER_CONNECTION_RETRY: Optional[bool] = Field(None, env="CELERY_BROKER_CONNECTION_RETRY")
    # Celery 6.0 introduced broker_connection_retry_on_startup separate flag
    CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP: Optional[bool] = Field(None, env="CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP")

    # Task configuration
    MAX_SCENES_PER_TASK: Optional[int] = Field(None, env="MAX_SCENES_PER_TASK")
    DEFAULT_SCENES_COUNT: Optional[int] = Field(None, env="DEFAULT_SCENES_COUNT")
    MAX_RETRY_ATTEMPTS: Optional[int] = Field(None, env="MAX_RETRY_ATTEMPTS")
    TASK_TIMEOUT_SECONDS: Optional[int] = Field(None, env="TASK_TIMEOUT_SECONDS")

    # Google Gemini AI settings (核心)
    GOOGLE_GEMINI_API_KEY: Optional[str] = Field(None, env="GOOGLE_GEMINI_API_KEY")
    GOOGLE_GEMINI_MODEL: Optional[str] = Field(None, env="GOOGLE_GEMINI_MODEL")
    # Legacy/alternative Gemini settings for compatibility
    GEMINI_MODEL_ID: Optional[str] = Field(None, env="GEMINI_MODEL_ID")
    GEMINI_API_KEYS: Optional[str] = Field(None, env="GEMINI_API_KEYS")

    # Fish Audio TTS settings (核心)
    FISH_AUDIO_API_KEY: Optional[str] = Field(None, env="FISH_AUDIO_API_KEY")
    FISH_AUDIO_VOICE_ID: Optional[str] = Field(None, env="FISH_AUDIO_VOICE_ID")
    FISH_AUDIO_API_URL: Optional[str] = Field(None, env="FISH_AUDIO_API_URL")
    # Legacy names (compat)
    FISHAUDIO_URL: Optional[str] = Field(None, env="FISHAUDIO_URL")
    FISHAUDIO_DEFAULT_VOICE_ID: Optional[str] = Field(None, env="FISHAUDIO_DEFAULT_VOICE_ID")

    # NCA Toolkit settings (核心)
    NCA_API_URL: Optional[str] = Field(None, env="NCA_API_URL")
    NCA_API_KEY: Optional[str] = Field(None, env="NCA_API_KEY")
    NCA_ASSET_BASE_URL: Optional[str] = Field(None, env="NCA_ASSET_BASE_URL")
    NCA_URL: Optional[str] = Field(None, env="NCA_URL")

    # Cloudinary settings (核心)
    CLOUDINARY_CLOUD_NAME: Optional[str] = Field(None, env="CLOUDINARY_CLOUD_NAME")
    CLOUDINARY_API_KEY: Optional[str] = Field(None, env="CLOUDINARY_API_KEY")
    CLOUDINARY_API_SECRET: Optional[str] = Field(None, env="CLOUDINARY_API_SECRET")

    # Liblib AI settings (可选)
    LIBLIB_ACCESS_KEY: Optional[str] = Field(None, env="LIBLIB_ACCESS_KEY")
    LIBLIB_SECRET_KEY: Optional[str] = Field(None, env="LIBLIB_SECRET_KEY")
    LIBLIB_API_URL: Optional[str] = Field(None, env="LIBLIB_API_URL")
    LIBLIB_CHECKPOINT_ID: Optional[str] = Field(None, env="LIBLIB_CHECKPOINT_ID")
    LIBLIB_MODEL_ID: Optional[str] = Field(None, env="LIBLIB_MODEL_ID")
    LIBLIB_LORA_ID: Optional[str] = Field(None, env="LIBLIB_LORA_ID")

    # Fal AI settings (可选)
    FAL_API_KEY: Optional[str] = Field(None, env="FAL_API_KEY")
    FAL_API_URL: Optional[str] = Field(None, env="FAL_API_URL")

    # ComfyUI settings (可选)
    COMFYUI_HOST: Optional[str] = Field(None, env="COMFYUI_HOST")
    COMFYUI_API_KEY: Optional[str] = Field(None, env="COMFYUI_API_KEY")

    # FFmpeg settings
    FFMPEG_BIN: Optional[str] = Field(None, env="FFMPEG_BIN")
    FFPROBE_BIN: Optional[str] = Field(None, env="FFPROBE_BIN")

    # Default BGM URL
    DEFAULT_BGM_URL: Optional[str] = Field(None, env="DEFAULT_BGM_URL")

    # Storage settings
    STORAGE_BASE_PATH: Optional[str] = Field(None, env="STORAGE_BASE_PATH")
    STORAGE_TEMP_PATH: Optional[str] = Field(None, env="STORAGE_TEMP_PATH")
    STORAGE_MAX_SIZE_MB: Optional[int] = Field(None, env="STORAGE_MAX_SIZE_MB")
    STORAGE_TYPE: Optional[str] = Field(None, env="STORAGE_TYPE")
    STORAGE_PUBLIC_BASE_URL: Optional[str] = Field(None, env="STORAGE_PUBLIC_BASE_URL")

    # Faster Whisper settings
    FASTER_WHISPER_MODEL: Optional[str] = Field(None, env="FASTER_WHISPER_MODEL")
    FASTER_WHISPER_DEVICE: Optional[str] = Field(None, env="FASTER_WHISPER_DEVICE")
    FASTER_WHISPER_DEVICE_INDEX: Optional[str] = Field(None, env="FASTER_WHISPER_DEVICE_INDEX")
    FASTER_WHISPER_COMPUTE_TYPE: Optional[str] = Field(None, env="FASTER_WHISPER_COMPUTE_TYPE")
    FASTER_WHISPER_DOWNLOAD_ROOT: Optional[str] = Field(None, env="FASTER_WHISPER_DOWNLOAD_ROOT")
    FASTER_WHISPER_BEAM_SIZE: Optional[int] = Field(None, env="FASTER_WHISPER_BEAM_SIZE")
    FASTER_WHISPER_VAD_FILTER: Optional[bool] = Field(None, env="FASTER_WHISPER_VAD_FILTER")
    FASTER_WHISPER_WORD_TIMESTAMPS: Optional[bool] = Field(None, env="FASTER_WHISPER_WORD_TIMESTAMPS")
    FASTER_WHISPER_TASK: Optional[str] = Field(None, env="FASTER_WHISPER_TASK")
    FASTER_WHISPER_LANGUAGE: Optional[str] = Field(None, env="FASTER_WHISPER_LANGUAGE")
    FASTER_WHISPER_TEMPERATURE: Optional[float] = Field(None, env="FASTER_WHISPER_TEMPERATURE")
    FASTER_WHISPER_CHUNK_LENGTH: Optional[float] = Field(None, env="FASTER_WHISPER_CHUNK_LENGTH")
    FASTER_WHISPER_INITIAL_PROMPT: Optional[str] = Field(None, env="FASTER_WHISPER_INITIAL_PROMPT")

    # Provider defaults configuration (JSON string like {"image": "liblib"})
    PROVIDER_DEFAULTS: Optional[str] = Field(None, env="PROVIDER_DEFAULTS")
    # Service concurrency defaults (JSON string like {"runninghub": {"image": 3}})
    SERVICE_CONCURRENCY_DEFAULTS: Optional[str] = Field(None, env="SERVICE_CONCURRENCY_DEFAULTS")
    
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE_PATH),
        case_sensitive=True,
        extra='ignore'  # 忽略 .env 中多余的字段
    )
    
    def get_provider_config(self, provider: str) -> Dict[str, Any]:
        """Get configuration for a specific service provider"""
        # Prefer DB-stored credentials (DB-only) for provider configuration.
        try:
            from app.database import get_db_session
            from app.models.service_config import ServiceCredential

            db = get_db_session()
            try:
                cred = db.query(ServiceCredential).filter(
                    ServiceCredential.service_name == provider.lower(),
                    ServiceCredential.is_active == True,
                ).order_by(ServiceCredential.id.desc()).first()
                if not cred:
                    raise RuntimeError(f"No credentials configured in database for provider '{provider}'")

                # Map common fields
                return {
                    "access_key": getattr(cred, "credential_key", None),
                    "secret_key": getattr(cred, "credential_secret", None),
                    "api_url": getattr(cred, "api_url", None),
                    "checkpoint_id": getattr(cred, "meta", None) or None,
                    "enabled": True,
                }
            finally:
                try:
                    db.close()
                except Exception:
                    pass
        except Exception as exc:
            raise RuntimeError(f"Failed to load provider configuration for '{provider}': {exc}")
    
    def get_available_providers(self) -> List[str]:
        """Get list of available/enabled service providers"""
        # Query DB for active service credentials to determine enabled providers
        try:
            from app.database import get_db_session
            from app.models.service_config import ServiceCredential

            db = get_db_session()
            try:
                rows = db.query(ServiceCredential.service_name).filter(ServiceCredential.is_active == True).distinct().all()
                return [r[0] for r in rows if r and r[0]]
            finally:
                try:
                    db.close()
                except Exception:
                    pass
        except Exception as exc:
            raise RuntimeError(f"Failed to determine available providers: {exc}")

    @property
    def resolved_gemini_api_key(self) -> Optional[str]:
        """
        DB-only: 仅从 `service_credentials` 表读取激活的 Gemini 凭证并返回其 credential_key。
        如果未找到或查询失败，返回 None。调用方应基于此抛出明确的配置异常。
        """
        try:
            # 延迟导入以避免循环依赖
            from app.database import get_db_session
            from app.models.service_config import ServiceCredential

            db = get_db_session()
            try:
                cred = db.query(ServiceCredential).filter(
                    ServiceCredential.service_name == 'gemini',
                    ServiceCredential.is_active == True,
                ).order_by(ServiceCredential.id.desc()).first()
                if cred and cred.credential_key:
                    return cred.credential_key
            finally:
                try:
                    db.close()
                except Exception:
                    pass
        except Exception:
            # 如果 DB 无法访问或查询出错，则返回 None（调用者会抛出配置异常）
            return None

    @property
    def resolved_gemini_model(self) -> Optional[str]:
        """读取 `service_options` 中默认的 Gemini 模型（model_id）。"""
        try:
            from app.database import get_db_session
            from app.models.service_config import ServiceOption

            db = get_db_session()
            try:
                opt = (
                    db.query(ServiceOption)
                    .filter(
                        ServiceOption.service_name == 'gemini',
                        ServiceOption.option_type == 'model_id',
                        ServiceOption.is_default == True,
                    )
                    .order_by(ServiceOption.id.desc())
                    .first()
                )
                if opt and opt.option_value:
                    return opt.option_value
            finally:
                try:
                    db.close()
                except Exception:
                    pass
        except Exception:
            return None
        return None

    @property
    def provider_defaults(self) -> Dict[str, str]:
        """Return default provider mapping, allowing JSON overrides via env."""
        if not self.PROVIDER_DEFAULTS:
            raise RuntimeError("PROVIDER_DEFAULTS must be configured explicitly")
        try:
            data = json.loads(self.PROVIDER_DEFAULTS)
            if isinstance(data, dict):
                override = {
                    str(k): str(v)
                    for k, v in data.items()
                    if isinstance(k, str) and isinstance(v, (str, int, float))
                }
                return override
        except json.JSONDecodeError:
            raise RuntimeError("PROVIDER_DEFAULTS is not valid JSON")

    @property
    def service_concurrency_defaults(self) -> Dict[str, Dict[str, int]]:
        if not self.SERVICE_CONCURRENCY_DEFAULTS:
            return {}
        try:
            raw = json.loads(self.SERVICE_CONCURRENCY_DEFAULTS)
        except json.JSONDecodeError:
            raise RuntimeError("SERVICE_CONCURRENCY_DEFAULTS is not valid JSON")
        result: Dict[str, Dict[str, int]] = {}
        if not isinstance(raw, dict):
            return result
        for service, payload in raw.items():
            if not isinstance(service, str) or not isinstance(payload, dict):
                continue
            nested: Dict[str, int] = {}
            for feature, value in payload.items():
                try:
                    nested[str(feature)] = int(value)
                except (TypeError, ValueError):
                    continue
            if nested:
                result[service.lower()] = nested
        return result

    @property
    def cors_allow_origins(self) -> List[str]:
        if self.CORS_ALLOW_ORIGINS:
            values = [item.strip() for item in self.CORS_ALLOW_ORIGINS.split(',')]
            origins = [value for value in values if value]
            if origins:
                return origins
        return [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]

@lru_cache()
def get_settings() -> Settings:
    return Settings()
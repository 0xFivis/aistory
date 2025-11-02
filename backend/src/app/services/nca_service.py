"""NCA Toolkit 远程服务封装（HTTP API）"""
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
import time
import json
from urllib.parse import urljoin

from .base import BaseService
from .exceptions import APIException, ConfigurationException, ValidationException
from app.models.service_config import ServiceCredential
from app.database import get_db_session
from app.core.http_client import create_http_client


class NCAService(BaseService):
    """NCA Toolkit 服务（通过远程 API 调用）"""

    def __init__(self, db: Optional[Session] = None, settings: Optional[object] = None):
        super().__init__(settings)
        self.db = db
        self.client = create_http_client("nca", timeout=90)
        self.file_base_url = getattr(self.settings, "NCA_ASSET_BASE_URL", None)
        self._load_credentials()
        self._validate_configuration()

    @property
    def service_name(self) -> str:
        return "NCA Toolkit"

    def _load_credentials(self) -> None:
        """从数据库加载 API Key 与 Base URL（DB-only 策略）"""
        session = self.db or get_db_session()
        should_close = self.db is None
        try:
            credential = session.query(ServiceCredential).filter(
                ServiceCredential.service_name == "nca",
                ServiceCredential.is_active == True,
            ).order_by(ServiceCredential.id.desc()).first()
            if not credential or not credential.credential_key:
                raise ConfigurationException(
                    "NCA API key not found in database (service_credentials). Add an active nca credential via /api/v1/config/credentials",
                    service_name=self.service_name,
                    required_envs=["service_credentials (nca)"],
                )
            if not credential.api_url:
                raise ConfigurationException(
                    "NCA base URL not configured in database (service_credentials.api_url)",
                    service_name=self.service_name,
                    required_envs=["service_credentials (nca.api_url)"],
                )
            self.api_key = credential.credential_key
            self.base_url = credential.api_url.rstrip("/")

            asset_base = self.file_base_url or None
            secret_value = credential.credential_secret or ""
            if secret_value:
                secret_value = secret_value.strip()
                parsed_secret: Optional[Dict[str, Any]] = None
                if secret_value.startswith("{") and secret_value.endswith("}"):
                    try:
                        parsed_secret = json.loads(secret_value)
                    except json.JSONDecodeError:
                        parsed_secret = None
                if parsed_secret and isinstance(parsed_secret, dict):
                    asset_base = parsed_secret.get("file_base_url") or parsed_secret.get("asset_base_url") or asset_base
                elif secret_value.lower().startswith("http"):
                    asset_base = secret_value

            description = (credential.description or "").strip()
            if description.lower().startswith("http"):
                asset_base = description

            if asset_base:
                self.file_base_url = asset_base.rstrip("/") + "/"
            elif self.base_url:
                self.file_base_url = self.base_url.rstrip("/") + "/"

            self.logger.info("Loaded NCA credentials from database")
        finally:
            if should_close:
                try:
                    session.close()
                except Exception:
                    pass

    def _validate_configuration(self) -> None:
        if not getattr(self, "api_key", None):
            raise ConfigurationException("NCA api_key is missing", service_name=self.service_name)
        if not getattr(self, "base_url", None):
            raise ConfigurationException("NCA base_url is missing", service_name=self.service_name)

    def _headers(self) -> Dict[str, str]:
        return {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
        }

    def _post(self, path: str, payload: Dict[str, Any], timeout: Optional[int] = None) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            raise ValidationException("Payload must be a JSON-able dict", field="payload")

        url = f"{self.base_url}{path if path.startswith('/') else '/' + path}"
        start = time.time()
        try:
            self._log_request(url, method="POST", payload=payload)
            response = self.client.post(url, json=payload, headers=self._headers(), timeout=timeout or 90)
            duration_ms = (time.time() - start) * 1000
            self._log_response(url, status_code=response.status_code, duration_ms=duration_ms)
            if response.status_code >= 400:
                preview = response.text[:2000] if response.text else "<empty>"
                self.logger.error(
                    "[%s] HTTP %s response body preview: %s",
                    self.service_name,
                    response.status_code,
                    preview,
                )
        except Exception as exc:
            self._log_error(exc, {"endpoint": path})
            raise APIException(
                f"Failed to call NCA API: {exc}",
                service_name=self.service_name,
            )

        # 尝试解析 JSON
        try:
            data = response.json()
        except Exception as exc:
            raise APIException(
                f"NCA API returned non-JSON response: {exc}",
                service_name=self.service_name,
                status_code=response.status_code,
            )

        if response.status_code >= 400 or data.get("error"):
            message = data.get("message") or data.get("error") or f"HTTP {response.status_code}"
            raise APIException(
                f"NCA API error: {message}",
                service_name=self.service_name,
                status_code=response.status_code,
                response_data=data,
            )
        return data

    def resolve_media_url(self, media_url: Optional[str]) -> Optional[str]:
        if not media_url:
            return None
        url_str = str(media_url).strip()
        if not url_str:
            return None
        if url_str.startswith("http://") or url_str.startswith("https://"):
            return url_str

        base = self.file_base_url or self.base_url
        if not base:
            return url_str

        base_with_slash = base if base.endswith("/") else base + "/"
        return urljoin(base_with_slash, url_str.lstrip("/"))

    # ---- 对应 n8n 中使用的几个端点 ----
    def get_media_metadata(self, media_url: str) -> Dict[str, Any]:
        if not media_url:
            raise ValidationException("media_url is required", field="media_url")
        return self._post("/v1/media/metadata", {"media_url": media_url})

    def compose(self, payload: Dict[str, Any], timeout: Optional[int] = None) -> Dict[str, Any]:
        """调用 /v1/ffmpeg/compose 执行合成任务"""
        return self._post("/v1/ffmpeg/compose", payload, timeout=timeout)

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        if not job_id:
            raise ValidationException("job_id is required", field="job_id")
        return self._post("/v1/toolkit/job/status", {"job_id": job_id})

    def image_to_video(self, image_url: str, length: int, frame_rate: int = 25, zoom_speed: int = 2, **extra) -> Dict[str, Any]:
        if not image_url:
            raise ValidationException("image_url is required", field="image_url")
        if length <= 0:
            raise ValidationException("length must be > 0", field="length")
        payload = {
            "image_url": image_url,
            "length": length,
            "frame_rate": frame_rate,
            "zoom_speed": zoom_speed,
        }
        if extra:
            payload.update(extra)
        return self._post("/v1/image/convert/video", payload)

    def process_video(self, compose_payload: Optional[Dict[str, Any]] = None, timeout: Optional[int] = None, **_: Any) -> Dict[str, Any]:
        """
        为兼容历史调用保留的包装方法。
        现在要求直接传入符合 /v1/ffmpeg/compose 的 payload。
        """
        if not compose_payload:
            raise ValidationException(
                "compose_payload is required when using NCA remote service",
                field="compose_payload",
            )
        return self.compose(compose_payload, timeout=timeout)

"""ComfyUI service wrapper (DB-only credential lookup)

Loads host and optional API key from `service_credentials` for service_name 'comfyui'.
"""
from typing import Optional, Dict, Any
from app.database import get_db_session
from app.models.service_config import ServiceCredential
from .base import BaseService
from .exceptions import ConfigurationException, APIException
from app.core.http_client import create_http_client


class ComfyUIService(BaseService):
    def __init__(self, settings: Optional[object] = None):
        super().__init__(settings)
        self._load_credentials()
        self.client = create_http_client("comfyui", timeout=60)

    @property
    def service_name(self) -> str:
        return "ComfyUI"

    def _load_credentials(self):
        db = None
        try:
            db = get_db_session()
            cred = db.query(ServiceCredential).filter(
                ServiceCredential.service_name == "comfyui",
                ServiceCredential.is_active == True,
            ).order_by(ServiceCredential.id.desc()).first()
            if not cred or not cred.api_url:
                raise ConfigurationException(
                    "ComfyUI host not found in database (service_credentials). Add an active comfyui credential with api_url pointing to the host",
                    service_name=self.service_name,
                    required_envs=["service_credentials (comfyui)"],
                )
            self.host = cred.api_url
            # optional api key stored in credential_key
            self.api_key = cred.credential_key
            self.logger.info("Loaded ComfyUI configuration from database")
        finally:
            try:
                if db:
                    db.close()
            except Exception:
                pass

    def ensure_configured(self):
        if not getattr(self, "host", None):
            raise ConfigurationException("ComfyUI host not configured in database", service_name=self.service_name)

    def text_to_image(self, prompt: str) -> Dict[str, Any]:
        self.ensure_configured()
        try:
            url = f"{self.host}/api/generate"
            headers = {"Content-Type": "application/json"}
            if getattr(self, "api_key", None):
                headers["Authorization"] = f"Bearer {self.api_key}"
            resp = self.client.post(url, json={"prompt": prompt}, headers=headers)
            if resp.status_code not in (200, 201):
                raise APIException(
                    message=f"ComfyUI API error: {resp.status_code}",
                    service_name=self.service_name,
                    status_code=resp.status_code,
                )
            return resp.json()
        except APIException:
            raise
        except Exception as e:
            raise APIException(
                message=f"Failed to call ComfyUI API: {e}",
                service_name=self.service_name,
            )

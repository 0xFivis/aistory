"""Fal AI service wrapper (DB-only credential lookup)

This is a minimal wrapper that enforces reading API key and API URL from
the `service_credentials` table (active credential). If missing, a
ConfigurationException is raised with a clear instruction to add the
credential via the config API.
"""
from typing import Optional, Dict, Any
from app.database import get_db_session
from app.models.service_config import ServiceCredential
from .base import BaseService
from .exceptions import ConfigurationException, APIException
from app.core.http_client import create_http_client


class FalService(BaseService):
    """Fal AI client enforcing DB-only credentials"""

    def __init__(self, settings: Optional[object] = None):
        super().__init__(settings)
        self._load_credentials()
        # create http client (proxy-aware)
        self.client = create_http_client("fal", timeout=60)

    @property
    def service_name(self) -> str:
        return "Fal AI"

    def _load_credentials(self):
        db = None
        try:
            db = get_db_session()
            cred = db.query(ServiceCredential).filter(
                ServiceCredential.service_name == "fal",
                ServiceCredential.is_active == True,
            ).order_by(ServiceCredential.id.desc()).first()
            if not cred or not cred.credential_key:
                raise ConfigurationException(
                    "Fal API key not found in database (service_credentials). Add an active fal credential via /api/v1/config/credentials",
                    service_name=self.service_name,
                    required_envs=["service_credentials (fal)"],
                )
            self.api_key = cred.credential_key
            self.api_url = cred.api_url or "https://api.fal.ai"
            self.logger.info("Loaded Fal credentials from database")
        finally:
            try:
                if db:
                    db.close()
            except Exception:
                pass

    def ensure_configured(self):
        if not getattr(self, "api_key", None):
            raise ConfigurationException("Fal credentials not configured in database", service_name=self.service_name)

    # Minimal wrapper methods (expand as needed)
    def image_to_video(self, image_url: str, prompt: str, duration: int = 6) -> Dict[str, Any]:
        """Call Fal image->video endpoint (minimal implementation)."""
        self.ensure_configured()
        try:
            url = f"{self.api_url}/v1/image-to-video"
            headers = {"Authorization": f"Key {self.api_key}", "Content-Type": "application/json"}
            payload = {"image_url": image_url, "prompt": prompt, "duration": duration}
            resp = self.client.post(url, json=payload, headers=headers)
            if resp.status_code not in (200, 201):
                raise APIException(
                    message=f"Fal API error: {resp.status_code}",
                    service_name=self.service_name,
                    status_code=resp.status_code,
                )
            return resp.json()
        except APIException:
            raise
        except Exception as e:
            raise APIException(
                message=f"Failed to call Fal API: {e}",
                service_name=self.service_name,
            )

"""
Cloudinary service wrapper for file uploads and URL management
"""
from typing import Optional, Dict, Any
import time

import cloudinary
import cloudinary.uploader
import cloudinary.api

from app.config.settings import Settings
from app.database import get_db_session
from app.models.service_config import ServiceCredential
from .base import BaseService
from .exceptions import APIException, ConfigurationException, ValidationException


class CloudinaryService(BaseService):
    """Service for interacting with Cloudinary API"""

    def __init__(self, settings: Optional[Settings] = None):
        super().__init__(settings)
        # Attempt to load Cloudinary credentials from DB (DB-only policy)
        self._load_db_credentials()
        self._configure_client()

    @property
    def service_name(self) -> str:
        return "Cloudinary"

    def _validate_configuration(self) -> None:
        # Defer strict validation to allow code paths that do not need Cloudinary
        return

    def _configure_client(self) -> None:
        # Expect DB-loaded attributes: cloud_name, api_key, api_secret
        if not (getattr(self, "cloud_name", None) and getattr(self, "api_key", None) and getattr(self, "api_secret", None)):
            self.logger.error("Cloudinary credentials not found in database (service_credentials). Uploads will fail until set")
            return
        cloudinary.config(
            cloud_name=self.cloud_name,
            api_key=self.api_key,
            api_secret=self.api_secret,
            secure=True,
        )
        self.logger.info("Cloudinary client configured from database credentials")

    def _load_db_credentials(self) -> None:
        """Load Cloudinary credentials from the service_credentials table (DB-only).

        This enforces the policy that credentials must exist in MySQL and
        prevents any fallback to environment variables.
        """
        db = None
        try:
            db = get_db_session()
            cred = db.query(ServiceCredential).filter(
                ServiceCredential.service_name == "cloudinary",
                ServiceCredential.is_active == True,
            ).order_by(ServiceCredential.id.desc()).first()
            if not cred:
                # leave attributes unset; ensure_configured()/ _configure_client will raise/log
                self.logger.warning("No active Cloudinary credential found in database")
                return

            self.cloud_name = cred.credential_key or getattr(cred, "cloud_name", None)
            # Historically some schemas stored api_key in credential_key and secret in credential_secret
            self.api_key = getattr(cred, "credential_key", None)
            self.api_secret = getattr(cred, "credential_secret", None)
            # Some entries may include api_url-like fields; keep for completeness
            self.api_url = getattr(cred, "api_url", None)
            self.logger.info("Loaded Cloudinary credentials from database")
        except Exception as e:
            self.logger.error(f"Failed to load Cloudinary credentials from database: {e}")
        finally:
            try:
                if db:
                    db.close()
            except Exception:
                pass

    def ensure_configured(self):
        if not (getattr(self, "cloud_name", None) and getattr(self, "api_key", None) and getattr(self, "api_secret", None)):
            raise ConfigurationException(
                "Cloudinary credentials are not configured in database (service_credentials). Add an active cloudinary credential via /api/v1/config/credentials",
                service_name=self.service_name,
                required_envs=["service_credentials (cloudinary)"],
            )

    def upload_file(
        self,
        file_path: str,
        folder: Optional[str] = None,
        public_id: Optional[str] = None,
        resource_type: str = "auto",
        overwrite: bool = True,
        **kwargs,
    ) -> Dict[str, Any]:
        """Upload a local file to Cloudinary

        Returns: dict with keys: url, secure_url, public_id, resource_type, format, bytes, width, height
        """
        if not file_path:
            raise ValidationException("file_path is required", field="file_path")

        self.ensure_configured()

        start = time.time()
        try:
            options = {
                "resource_type": resource_type,
                "overwrite": overwrite,
                **({"folder": folder} if folder else {}),
                **({"public_id": public_id} if public_id else {}),
                **kwargs,
            }
            self._log_request("cloudinary.uploader.upload", method="POST", options=options)
            result = cloudinary.uploader.upload(file_path, **options)
            duration_ms = (time.time() - start) * 1000
            self._log_response("cloudinary.uploader.upload", 200, duration_ms)
            return result
        except Exception as e:
            raise APIException(
                f"Upload failed: {str(e)}",
                service_name=self.service_name,
            )

    def delete(self, public_id: str, resource_type: str = "image") -> Dict[str, Any]:
        if not public_id:
            raise ValidationException("public_id is required", field="public_id")
        self.ensure_configured()
        try:
            self._log_request("cloudinary.uploader.destroy", method="POST", public_id=public_id)
            result = cloudinary.uploader.destroy(public_id, resource_type=resource_type)
            self._log_response("cloudinary.uploader.destroy", 200, 0)
            return result
        except Exception as e:
            raise APIException(
                f"Delete failed: {str(e)}",
                service_name=self.service_name,
            )

    def generate_url(self, public_id: str, resource_type: str = "image", **options) -> str:
        if not public_id:
            raise ValidationException("public_id is required", field="public_id")
        try:
            url, _ = cloudinary.CloudinaryImage(public_id).build_url(resource_type=resource_type, **options)
            return url
        except Exception as e:
            raise APIException(
                f"URL generation failed: {str(e)}",
                service_name=self.service_name,
            )

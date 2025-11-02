"""Liblib AI 图像生成服务"""
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.core.http_client import create_http_client
from app.models.service_config import ServiceCredential, ServiceOption
from .base import BaseService
from .exceptions import APIException, ConfigurationException, ValidationException

class LiblibService(BaseService):
    """Liblib AI 图像生成服务类"""

    def __init__(self, db: Session, lora_id: Optional[str] = None, checkpoint_id: Optional[str] = None):
        super().__init__()
        self.db = db
        self._load_credentials()
        self._load_checkpoint_config(checkpoint_id)
        self._load_lora_config(lora_id)
        self.client = create_http_client("liblib", timeout=60)
        # Validate after loading credentials and config
        self._validate_configuration()

    @property
    def service_name(self) -> str:
        return "Liblib AI"

    def _validate_configuration(self) -> None:
        if not self.api_key:
            raise ConfigurationException("Liblib API Key not configured", service_name=self.service_name)
        if not self.api_url:
            raise ConfigurationException("Liblib API URL not configured", service_name=self.service_name)

    def _load_credentials(self):
        credential = self.db.query(ServiceCredential).filter(
            ServiceCredential.service_name == "liblib",
            ServiceCredential.is_active == True
        ).first()
        if not credential:
            raise ConfigurationException("Liblib credentials not found in database", service_name=self.service_name)
        self.api_key = credential.credential_key
        self.api_secret = credential.credential_secret
        if not credential.api_url:
            raise ConfigurationException("Liblib API URL not configured in database", service_name=self.service_name)
        self.api_url = credential.api_url

    def _load_checkpoint_config(self, checkpoint_id: Optional[str] = None):
        option_type_candidates = ("checkpoint_id", "model_id")
        if checkpoint_id:
            option = self.db.query(ServiceOption).filter(
                ServiceOption.service_name == "liblib",
                ServiceOption.option_type.in_(option_type_candidates),
                ServiceOption.option_key == checkpoint_id
            ).first()
            if not option:
                self.checkpoint_id = checkpoint_id
                self.checkpoint_name = checkpoint_id
            else:
                self.checkpoint_id = option.option_value
                self.checkpoint_name = option.option_name
        else:
            option = self.db.query(ServiceOption).filter(
                ServiceOption.service_name == "liblib",
                ServiceOption.option_type.in_(option_type_candidates),
                ServiceOption.is_default == True
            ).first()
            if not option:
                raise ConfigurationException("No default Liblib checkpoint configured", service_name=self.service_name)
            self.checkpoint_id = option.option_value
            self.checkpoint_name = option.option_name

    def _load_lora_config(self, lora_id: Optional[str] = None):
        if lora_id:
            option = self.db.query(ServiceOption).filter(
                ServiceOption.service_name == "liblib",
                ServiceOption.option_type == "lora_id",
                ServiceOption.option_key == lora_id
            ).first()
            if not option:
                self.lora_id = lora_id
                self.lora_name = lora_id
            else:
                self.lora_id = option.option_value
                self.lora_name = option.option_name
        else:
            option = self.db.query(ServiceOption).filter(
                ServiceOption.service_name == "liblib",
                ServiceOption.option_type == "lora_id",
                ServiceOption.is_default == True
            ).first()
            if not option:
                self.lora_id = None
                self.lora_name = None
            else:
                self.lora_id = option.option_value
                self.lora_name = option.option_name

    def generate_image(self, prompt: str, negative_prompt: Optional[str] = None, width: int = 1024, height: int = 1024, steps: int = 30, seed: Optional[int] = None) -> Dict[str, Any]:
        if not prompt or not prompt.strip():
            raise ValidationException("prompt cannot be empty", field="prompt")
        url = f"{self.api_url}/v1/sdapi/txt2img"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "X-Api-Secret": self.api_secret,
            "Content-Type": "application/json"
        }
        payload = {
            "prompt": prompt,
            "negative_prompt": negative_prompt or "",
            "width": width,
            "height": height,
            "steps": steps,
            "seed": seed,
            "model_id": self.checkpoint_id,
            "lora_id": self.lora_id
        }
        try:
            self._log_request("generate_image", method="POST", prompt=prompt)
            response = self.client.post(url, json=payload, headers=headers)
            if response.status_code == 200:
                data = response.json()
                self._log_response("generate_image", status_code=200)
                return data
            else:
                error_msg = f"Liblib API error: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", error_msg)
                except:
                    error_msg = response.text or error_msg
                self._log_error("generate_image", error_msg)
                raise APIException(
                    message=error_msg,
                    service_name=self.service_name,
                    status_code=response.status_code,
                    response_data=error_data if 'error_data' in locals() else None,
                )
        except APIException:
            raise
        except Exception as e:
            self._log_error("generate_image", str(e))
            raise APIException(
                message=f"Failed to call Liblib API: {str(e)}",
                service_name=self.service_name,
            )

    def close(self):
        if hasattr(self, 'client'):
            self.client.close()

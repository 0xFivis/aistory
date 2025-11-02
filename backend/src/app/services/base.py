"""
Base service class with common functionality
"""
import logging
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod

from app.config.settings import Settings, get_settings
from .exceptions import ConfigurationException


class BaseService(ABC):
    """Base class for all external service integrations"""
    
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        # Note: child services should perform validation after they have
        # loaded DB credentials or other required attributes. Avoid calling
        # `_validate_configuration` here to prevent validation running before
        # child initializers set necessary fields.
    
    @property
    @abstractmethod
    def service_name(self) -> str:
        """Return the service name for logging and error messages"""
        pass
    
    @abstractmethod
    def _validate_configuration(self) -> None:
        """
        Validate that required configuration is present.
        Raise ConfigurationException if invalid.
        """
        pass
    
    def _log_request(self, endpoint: str, method: str = "POST", **kwargs):
        """Log outgoing API request"""
        self.logger.info(
            f"[{self.service_name}] {method} {endpoint}",
            extra={"service": self.service_name, "endpoint": endpoint, **kwargs}
        )
    
    def _log_response(self, endpoint: str, status_code: int, duration_ms: float):
        """Log API response"""
        self.logger.info(
            f"[{self.service_name}] Response {status_code} from {endpoint} ({duration_ms:.2f}ms)",
            extra={
                "service": self.service_name,
                "endpoint": endpoint,
                "status_code": status_code,
                "duration_ms": duration_ms,
            }
        )
    
    def _log_error(self, error: Exception | str, context: Optional[Dict[str, Any] | str] = None):
        """Log service error"""
        extra: Dict[str, Any] = {"service": self.service_name}
        if context:
            if isinstance(context, dict):
                extra.update(context)
            else:
                extra["context"] = context

        if isinstance(error, Exception):
            self.logger.error(
                f"[{self.service_name}] Error: {str(error)}",
                exc_info=True,
                extra=extra,
            )
        else:
            self.logger.error(
                f"[{self.service_name}] Error: {str(error)}",
                extra=extra,
            )

"""
Custom exceptions for service layer
"""
from typing import Optional, Any, Dict


class ServiceException(Exception):
    """Base exception for all service errors"""
    
    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code or "SERVICE_ERROR"
        self.details = details or {}
        super().__init__(self.message)


class APIException(ServiceException):
    """Exception raised when external API calls fail"""
    
    def __init__(
        self,
        message: str,
        service_name: str,
        status_code: Optional[int] = None,
        response_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        self.service_name = service_name
        self.status_code = status_code
        self.response_data = response_data
        
        details = {
            "service": service_name,
            "status_code": status_code,
            "response": response_data,
            **kwargs
        }
        
        super().__init__(
            message=f"[{service_name}] {message}",
            code="API_ERROR",
            details=details
        )


class ConfigurationException(ServiceException):
    """Exception raised when service configuration is invalid or missing"""
    
    def __init__(self, message: str, service_name: str, **kwargs):
        self.service_name = service_name
        super().__init__(
            message=f"[{service_name}] Configuration error: {message}",
            code="CONFIG_ERROR",
            details={"service": service_name, **kwargs}
        )


class ValidationException(ServiceException):
    """Exception raised when input validation fails"""
    
    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        self.field = field
        details = {"field": field, **kwargs} if field else kwargs
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            details=details
        )


class TimeoutException(ServiceException):
    """Exception raised when operation times out"""
    
    def __init__(self, message: str, timeout_seconds: Optional[int] = None, **kwargs):
        self.timeout_seconds = timeout_seconds
        details = {"timeout_seconds": timeout_seconds, **kwargs}
        super().__init__(
            message=message,
            code="TIMEOUT_ERROR",
            details=details
        )


class RetryException(ServiceException):
    """Exception raised when retry attempts are exhausted"""
    
    def __init__(
        self,
        message: str,
        attempts: int,
        last_error: Optional[Exception] = None,
        **kwargs
    ):
        self.attempts = attempts
        self.last_error = last_error
        details = {
            "attempts": attempts,
            "last_error": str(last_error) if last_error else None,
            **kwargs
        }
        super().__init__(
            message=message,
            code="RETRY_EXHAUSTED",
            details=details
        )


class ResourceNotFoundException(ServiceException):
    """Exception raised when a requested resource is not found"""
    
    def __init__(self, resource_type: str, resource_id: Any, **kwargs):
        self.resource_type = resource_type
        self.resource_id = resource_id
        super().__init__(
            message=f"{resource_type} with id {resource_id} not found",
            code="RESOURCE_NOT_FOUND",
            details={"resource_type": resource_type, "resource_id": resource_id, **kwargs}
        )

"""Runninghub service wrapper for workflow execution (DB-only credentials)."""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.database import get_db_session
from app.models.service_config import ServiceCredential
from .base import BaseService
from .exceptions import APIException, ConfigurationException, ValidationException
from app.core.http_client import create_http_client


class RunningHubService(BaseService):
    """Client for Runninghub workflow open API."""

    def __init__(self, db: Optional[Session] = None, settings: Optional[object] = None):
        super().__init__(settings)
        self._db = db
        self.client = create_http_client("runninghub", timeout=60)
        self._load_credentials()
        self._validate_configuration()

    @property
    def service_name(self) -> str:
        return "Runninghub"

    def _load_credentials(self) -> None:
        session = self._db or get_db_session()
        should_close = self._db is None
        try:
            credential = (
                session.query(ServiceCredential)
                .filter(
                    ServiceCredential.service_name == "runninghub",
                    ServiceCredential.is_active == True,  # noqa: E712
                )
                .order_by(ServiceCredential.id.desc())
                .first()
            )
            if not credential or not credential.credential_key:
                raise ConfigurationException(
                    "Runninghub API key not found in database (service_credentials). Add an active runninghub credential via /api/v1/config/credentials",
                    service_name=self.service_name,
                    required_envs=["service_credentials (runninghub)"],
                )
            self.api_key = credential.credential_key
            if not credential.api_url:
                raise ConfigurationException(
                    "Runninghub base URL not configured in database (service_credentials.api_url)",
                    service_name=self.service_name,
                    required_envs=["service_credentials (runninghub.api_url)"],
                )
            self.base_url = credential.api_url.rstrip("/")
        finally:
            if should_close:
                try:
                    session.close()
                except Exception:
                    pass

    def _validate_configuration(self) -> None:
        if not getattr(self, "api_key", None):
            raise ConfigurationException("Runninghub api_key is missing", service_name=self.service_name)
        if not getattr(self, "base_url", None):
            raise ConfigurationException("Runninghub base_url is missing", service_name=self.service_name)

    def _headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        host = urlparse(self.base_url).netloc
        if host:
            headers["Host"] = host
        return headers

    def _post(self, path: str, payload: Dict[str, Any], timeout: Optional[int] = None) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            raise ValidationException("Payload must be a JSON-able dict", field="payload")

        url = f"{self.base_url}{path if path.startswith('/') else '/' + path}"
        start = time.time()
        try:
            self._log_request(url, method="POST", payload=payload)
            response = self.client.post(url, json=payload, headers=self._headers(), timeout=timeout or 60)
            duration_ms = (time.time() - start) * 1000
            self._log_response(url, status_code=response.status_code, duration_ms=duration_ms)
        except Exception as exc:  # pragma: no cover - network failure path
            self._log_error(exc, {"endpoint": path})
            raise APIException(
                f"Failed to call Runninghub API: {exc}",
                service_name=self.service_name,
            )

        try:
            data = response.json()
        except Exception as exc:  # pragma: no cover - non-json response
            raise APIException(
                f"Runninghub API returned non-JSON response: {exc}",
                service_name=self.service_name,
                status_code=response.status_code,
            )

        if response.status_code >= 400:
            raise APIException(
                f"HTTP {response.status_code}",
                service_name=self.service_name,
                status_code=response.status_code,
                response_data=data,
            )
        return data

    def create_task(
        self,
        workflow_id: str,
        node_info_list: Optional[List[Dict[str, Any]]] = None,
        instance_type: str = "plus",
        extra_params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        if not workflow_id:
            raise ValidationException("workflow_id is required", field="workflow_id")

        payload: Dict[str, Any] = {
            "apiKey": self.api_key,
            "workflowId": workflow_id,
            "instanceType": instance_type,
        }
        if node_info_list:
            payload["nodeInfoList"] = node_info_list
        if extra_params:
            payload.update(extra_params)
        return self._post("/task/openapi/create", payload, timeout=timeout)

    def get_outputs(self, task_id: str, timeout: Optional[int] = None) -> Dict[str, Any]:
        if not task_id:
            raise ValidationException("task_id is required", field="task_id")
        payload = {"apiKey": self.api_key, "taskId": task_id}
        return self._post("/task/openapi/outputs", payload, timeout=timeout)

    @staticmethod
    def _interpret_status(payload: Optional[Dict[str, Any]]) -> str:
        if not isinstance(payload, dict):
            return "error"

        raw_msg = payload.get("msg") or payload.get("message") or ""
        msg = str(raw_msg).strip()
        msg_upper = msg.upper()

        if msg == "success":
            return "success"
        if "RUNNING" in msg_upper:
            return "pending"
        if "QUEUE" in msg_upper:
            return "pending"
        if "ERROR" in msg_upper or "FAIL" in msg_upper:
            return "error"
        if msg:
            return "error"

        code = payload.get("code")
        if code is not None:
            code_str = str(code).strip().upper()
            if code_str in {"0", "200"}:
                return "success"

        return "error"

    def wait_for_task(
        self,
        task_id: str,
        *,
        max_attempts: int = 6,
        interval_seconds: float = 5.0,
        initial_delay_seconds: float = 0.0,
        timeout: Optional[int] = None,
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        """Poll Runninghub outputs until completion or attempts exhausted."""
        last_payload: Optional[Dict[str, Any]] = None
        if initial_delay_seconds > 0:
            time.sleep(initial_delay_seconds)
        for attempt in range(max(1, max_attempts)):
            last_payload = self.get_outputs(task_id, timeout=timeout)
            status = self._interpret_status(last_payload)
            if status in {"success", "error"}:
                return status, last_payload
            if attempt < max_attempts - 1 and interval_seconds > 0:
                time.sleep(interval_seconds)
        return "pending", last_payload

    @staticmethod
    def extract_task_id(payload: Optional[Dict[str, Any]]) -> Optional[str]:
        if not isinstance(payload, dict):
            return None
        data = payload.get("data")
        if isinstance(data, dict):
            task_id = data.get("taskId") or data.get("task_id")
            if task_id:
                return str(task_id)
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    task_id = item.get("taskId") or item.get("task_id")
                    if task_id:
                        return str(task_id)
        if "taskId" in payload:
            return str(payload.get("taskId"))
        return None

    @staticmethod
    def extract_file_entries(payload: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not isinstance(payload, dict):
            return []
        data = payload.get("data")
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        if isinstance(data, dict):
            if isinstance(data.get("list"), list):
                return [item for item in data["list"] if isinstance(item, dict)]
            return [data]
        return []

    @staticmethod
    def extract_error_message(payload: Optional[Dict[str, Any]]) -> Optional[str]:
        if not isinstance(payload, dict):
            return None
        if payload.get("msg"):
            return str(payload.get("msg"))
        if payload.get("message"):
            return str(payload.get("message"))
        return None

    @staticmethod
    def is_success_payload(payload: Optional[Dict[str, Any]]) -> bool:
        if not isinstance(payload, dict):
            return False
        code = payload.get("code")
        if isinstance(code, (int, float)):
            if int(code) in {0, 200}:
                return True
        if isinstance(code, str):
            if code.strip().upper() in {"0", "200"}:
                return True
        msg = str(payload.get("msg") or payload.get("message") or "").strip().lower()
        return msg in {"success", "ok", "done", "finished"}

    @staticmethod
    def is_concurrency_limited(payload: Optional[Dict[str, Any]]) -> bool:
        if not isinstance(payload, dict):
            return False
        code = str(payload.get("code") or "").upper()
        msg = str(payload.get("msg") or payload.get("message") or "").upper()
        keywords = {"APIKEY_IS_RUNNING", "KEY_IS_RUNNING", "IS_RUNNING", "TOO_MANY_TASKS"}
        return any(keyword in code for keyword in keywords) or any(keyword in msg for keyword in keywords)


__all__ = ["RunningHubService"]

"""Global concurrency manager for external service usage."""
from __future__ import annotations

import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import timedelta
from typing import Dict, Generator, Optional, Tuple

from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.database import get_db_session
from app.models.concurrency import ServiceConcurrencyLimit, ServiceConcurrencySlot
from app.services.exceptions import APIException
from app.utils.timezone import naive_now

_DEFAULT_WAIT_INTERVAL = 5.0
_DEFAULT_WAIT_TIMEOUT = 60.0
_DEFAULT_SLOT_TIMEOUT = 600.0

_ALLOWED_RELEASE_STATUSES = {
    ServiceConcurrencySlot.STATUS_RELEASED,
    ServiceConcurrencySlot.STATUS_ERROR,
    ServiceConcurrencySlot.STATUS_TIMEOUT,
    ServiceConcurrencySlot.STATUS_EXPIRED,
}


@dataclass
class SlotLimit:
    service_name: str
    feature: Optional[str]
    max_slots: int
    wait_interval: float
    wait_timeout: Optional[float]
    slot_timeout: float


@dataclass
class SlotToken:
    service_name: str
    feature: Optional[str]
    slot_id: Optional[int]
    resource_id: Optional[str]
    unlimited: bool = False

    @property
    def is_real(self) -> bool:
        return not self.unlimited and self.slot_id is not None


class ConcurrencyManager:
    """Coordinate provider concurrency across workers/processes."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._limit_cache: Dict[tuple[str, Optional[str]], Tuple[SlotLimit, float]] = {}
        self._cache_lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def acquire(
        self,
        service_name: str,
        *,
        feature: Optional[str] = None,
        resource_id: Optional[str] = None,
        wait_timeout: Optional[float] = None,
        slot_timeout: Optional[float] = None,
        metadata: Optional[dict] = None,
    ) -> SlotToken:
        """Acquire a slot for a given service/feature.

        Raises APIException when wait_timeout is reached.
        Returns a token that must be released when work is done.
        """

        service_key = service_name.lower().strip()
        feature_key = feature.lower().strip() if feature else None

        limit = self._resolve_limit(service_key, feature_key)
        if limit is None or limit.max_slots <= 0:
            # No limit configured, treat as unlimited.
            return SlotToken(service_key, feature_key, slot_id=None, resource_id=resource_id, unlimited=True)

        wait_timeout = wait_timeout if wait_timeout is not None else limit.wait_timeout
        slot_timeout = slot_timeout if slot_timeout is not None else limit.slot_timeout
        wait_interval = max(limit.wait_interval, 1.0)
        deadline = time.monotonic() + wait_timeout if wait_timeout else None

        # Opportunistically clean up expired slots for this service
        self._cleanup_expired_for(service_key, feature_key)

        session: Optional[Session] = None
        try:
            while True:
                if deadline and time.monotonic() >= deadline:
                    raise APIException(
                        "外部服务并发名额已满，请稍后重试",
                        service_name=service_name,
                    )

                session = get_db_session()
                try:
                    slot_id = self._try_acquire_slot(
                        session,
                        limit,
                        resource_id=resource_id,
                        slot_timeout=slot_timeout,
                        metadata=metadata,
                    )
                    if slot_id is not None:
                        return SlotToken(service_key, feature_key, slot_id=slot_id, resource_id=resource_id)
                finally:
                    if session:
                        session.close()
                        session = None

                time.sleep(wait_interval)
        finally:
            if session:
                session.close()

    def release(
        self,
        token: SlotToken,
        *,
        status: str = ServiceConcurrencySlot.STATUS_RELEASED,
        metadata: Optional[dict] = None,
    ) -> None:
        if token.unlimited or not token.slot_id:
            return

        session = get_db_session()
        try:
            slot = session.get(ServiceConcurrencySlot, token.slot_id)
            if not slot:
                return
            if slot.status != ServiceConcurrencySlot.STATUS_ACTIVE:
                return

            release_status = status if status in _ALLOWED_RELEASE_STATUSES else ServiceConcurrencySlot.STATUS_RELEASED
            slot.mark_released(release_status, metadata=metadata)
            session.commit()
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()
    def update_metadata(self, token: SlotToken, metadata: dict) -> None:
        if token.unlimited or not token.slot_id or not metadata:
            return

        session = get_db_session()
        try:
            slot = session.get(ServiceConcurrencySlot, token.slot_id)
            if not slot or slot.status != ServiceConcurrencySlot.STATUS_ACTIVE:
                return
            existing = slot.meta_json if isinstance(slot.meta_json, dict) else {}
            existing.update(metadata)
            slot.meta_json = existing
            session.commit()
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()

    def purge_expired(self, batch_size: int = 100) -> int:
        """Mark expired slots as freed. Returns number of records updated."""

        session = get_db_session()
        try:
            now = naive_now()
            expired = (
                session.query(ServiceConcurrencySlot)
                .filter(
                    ServiceConcurrencySlot.status == ServiceConcurrencySlot.STATUS_ACTIVE,
                    ServiceConcurrencySlot.expires_at != None,  # noqa: E711
                    ServiceConcurrencySlot.expires_at < now,
                )
                .limit(batch_size)
                .all()
            )
            for slot in expired:
                slot.mark_released(ServiceConcurrencySlot.STATUS_EXPIRED)
            if expired:
                session.commit()
            return len(expired)
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()

    @contextmanager
    def reserve(
        self,
        service_name: str,
        *,
        feature: Optional[str] = None,
        resource_id: Optional[str] = None,
        wait_timeout: Optional[float] = None,
        slot_timeout: Optional[float] = None,
        metadata: Optional[dict] = None,
        release_status: str = ServiceConcurrencySlot.STATUS_RELEASED,
    ) -> Generator[SlotToken, None, None]:
        token = self.acquire(
            service_name,
            feature=feature,
            resource_id=resource_id,
            wait_timeout=wait_timeout,
            slot_timeout=slot_timeout,
            metadata=metadata,
        )
        try:
            yield token
        except Exception:
            self.release(token, status=ServiceConcurrencySlot.STATUS_ERROR, metadata=metadata)
            raise
        else:
            self.release(token, status=release_status, metadata=metadata)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _cleanup_expired_for(self, service_name: str, feature: Optional[str]) -> None:
        session = get_db_session()
        try:
            now = naive_now()
            query = session.query(ServiceConcurrencySlot).filter(
                ServiceConcurrencySlot.service_name == service_name,
                ServiceConcurrencySlot.status == ServiceConcurrencySlot.STATUS_ACTIVE,
                ServiceConcurrencySlot.expires_at != None,  # noqa: E711
                ServiceConcurrencySlot.expires_at < now,
            )
            if feature is None:
                query = query.filter(ServiceConcurrencySlot.feature == None)  # noqa: E711
            else:
                query = query.filter(ServiceConcurrencySlot.feature == feature)

            expired = query.limit(50).all()
            if not expired:
                return

            for slot in expired:
                slot.mark_released(ServiceConcurrencySlot.STATUS_EXPIRED)
            session.commit()
        except SQLAlchemyError:
            session.rollback()
        finally:
            session.close()

    def _resolve_limit(self, service_name: str, feature: Optional[str]) -> Optional[SlotLimit]:
        cache_key = (service_name, feature)
        now = time.monotonic()
        with self._cache_lock:
            cached = self._limit_cache.get(cache_key)
            if cached and cached[1] > now:
                return cached[0]

        limit_record = self._load_limit_from_db(service_name, feature)
        if limit_record is None:
            default_limit = self._load_default_limit(service_name, feature)
            if default_limit:
                with self._cache_lock:
                    self._limit_cache[cache_key] = (default_limit, now + 5.0)
                return default_limit
            return None

        limit = SlotLimit(
            service_name=limit_record.service_name,
            feature=limit_record.feature,
            max_slots=max(limit_record.max_slots or 0, 0),
            wait_interval=max(limit_record.wait_interval(), 1.0),
            wait_timeout=float(limit_record.wait_timeout_seconds) if limit_record.wait_timeout_seconds else None,
            slot_timeout=max(float(limit_record.slot_timeout_seconds or _DEFAULT_SLOT_TIMEOUT), 1.0),
        )
        with self._cache_lock:
            self._limit_cache[cache_key] = (limit, now + 5.0)
        return limit

    def _load_limit_from_db(self, service_name: str, feature: Optional[str]) -> Optional[ServiceConcurrencyLimit]:
        session = get_db_session()
        try:
            query = session.query(ServiceConcurrencyLimit).filter(
                ServiceConcurrencyLimit.service_name == service_name,
                ServiceConcurrencyLimit.enabled == True,  # noqa: E712
            )
            if feature is not None:
                query = query.filter(ServiceConcurrencyLimit.feature == feature)
                limit = query.first()
                if limit:
                    return limit
            # fallback to service-level limit
            query = session.query(ServiceConcurrencyLimit).filter(
                ServiceConcurrencyLimit.service_name == service_name,
                ServiceConcurrencyLimit.feature == None,  # noqa: E711
                ServiceConcurrencyLimit.enabled == True,  # noqa: E712
            )
            return query.first()
        finally:
            session.close()

    def _load_default_limit(self, service_name: str, feature: Optional[str]) -> Optional[SlotLimit]:
        defaults = getattr(self._settings, "service_concurrency_defaults", {}) or {}
        service_defaults = defaults.get(service_name)
        if not isinstance(service_defaults, dict):
            return None
        value = service_defaults.get(feature or "__all__")
        if value is None and feature is not None:
            value = service_defaults.get("__all__")
        try:
            max_slots = int(value)
        except (TypeError, ValueError):
            return None
        if max_slots <= 0:
            return None
        return SlotLimit(
            service_name=service_name,
            feature=feature,
            max_slots=max_slots,
            wait_interval=_DEFAULT_WAIT_INTERVAL,
            wait_timeout=_DEFAULT_WAIT_TIMEOUT,
            slot_timeout=_DEFAULT_SLOT_TIMEOUT,
        )

    def _try_acquire_slot(
        self,
        session: Session,
        limit: SlotLimit,
        *,
        resource_id: Optional[str],
        slot_timeout: float,
        metadata: Optional[dict],
    ) -> Optional[int]:
        try:
            now = naive_now()
            expires_at = now + timedelta(seconds=max(slot_timeout, 1.0))
            with session.begin():
                active_slots = (
                    session.query(ServiceConcurrencySlot)
                    .filter(
                        ServiceConcurrencySlot.service_name == limit.service_name,
                        ServiceConcurrencySlot.feature == limit.feature,
                        ServiceConcurrencySlot.status == ServiceConcurrencySlot.STATUS_ACTIVE,
                        or_(
                            ServiceConcurrencySlot.expires_at == None,  # noqa: E711
                            ServiceConcurrencySlot.expires_at > now,
                        ),
                    )
                    .with_for_update()
                    .all()
                )

                if len(active_slots) >= limit.max_slots:
                    return None

                slot = ServiceConcurrencySlot(
                    service_name=limit.service_name,
                    feature=limit.feature,
                    resource_id=resource_id,
                    expires_at=expires_at,
                    meta_json=metadata or None,
                )
                session.add(slot)
                session.flush()
                return slot.id
        except SQLAlchemyError:
            session.rollback()
            raise


# module-level singleton
concurrency_manager = ConcurrencyManager()

__all__ = ["concurrency_manager", "ConcurrencyManager", "SlotToken"]

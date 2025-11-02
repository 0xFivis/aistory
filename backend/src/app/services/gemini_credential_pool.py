"""Gemini-specific credential pool.

Provides an atomic acquire() to select an active Gemini API key that has not
been used within a cooldown window. Uses row-level locking (SELECT FOR UPDATE
SKIP LOCKED) to avoid concurrent allocation of the same key.
"""
from datetime import timedelta
from typing import Optional
from sqlalchemy import or_, asc
from sqlalchemy.orm import Session

from app.database import get_db_session
from app.models.service_config import ServiceCredential
from app.services.exceptions import ConfigurationException
from app.utils.timezone import naive_now


DEFAULT_COOLDOWN_SECONDS = 300


class GeminiCredentialPool:
    @staticmethod
    def acquire(cooldown_seconds: int = DEFAULT_COOLDOWN_SECONDS, allow_reuse_after_exhaust: bool = False) -> ServiceCredential:
        db: Session = get_db_session()
        try:
            now = naive_now()
            cutoff = now - timedelta(seconds=cooldown_seconds)

            # First try: find an active credential not used within cooldown (including never-used)
            q = (
                db.query(ServiceCredential)
                .filter(ServiceCredential.service_name == "gemini")
                .filter(ServiceCredential.is_active == True)
                .filter(or_(ServiceCredential.last_used_at == None, ServiceCredential.last_used_at <= cutoff))
                .order_by(asc(ServiceCredential.last_used_at))
                .with_for_update(skip_locked=True)
            )

            cred = q.first()
            if cred is None and allow_reuse_after_exhaust:
                # fallback to least-recently-used even if within cooldown
                q2 = (
                    db.query(ServiceCredential)
                    .filter(ServiceCredential.service_name == "gemini")
                    .filter(ServiceCredential.is_active == True)
                    .order_by(asc(ServiceCredential.last_used_at))
                    .with_for_update(skip_locked=True)
                )
                cred = q2.first()

            if cred is None:
                raise ConfigurationException(
                    "No available Gemini API keys: all keys are in cooldown or none configured",
                    service_name="gemini",
                )

            # mark used now
            cred.last_used_at = now
            db.add(cred)
            db.commit()
            db.refresh(cred)
            return cred
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from functools import lru_cache

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None  # type: ignore

from app.config.settings import get_settings

logger = logging.getLogger(__name__)

_DEFAULT_TZ = "UTC"


@lru_cache(maxsize=1)
def _resolve_timezone():
    settings = get_settings()
    tz_name = settings.APP_TIMEZONE or _DEFAULT_TZ
    if ZoneInfo is None:
        logger.warning("ZoneInfo module not available; falling back to naive datetimes")
        return None
    try:
        return ZoneInfo(tz_name)
    except Exception:
        logger.exception("Failed to load timezone '%s', falling back to UTC", tz_name)
        try:
            return ZoneInfo(_DEFAULT_TZ)
        except Exception:
            return None


def get_timezone():
    return _resolve_timezone()


def now(aware: bool = False):
    tz = get_timezone()
    if tz is None:
        current = datetime.now(timezone.utc)
        return current if aware else current.replace(tzinfo=None)
    current = datetime.now(tz)
    return current if aware else current.replace(tzinfo=None)


def aware_now():
    return now(aware=True)


def naive_now():
    return now(aware=False)


def to_local(dt, aware: bool = False):
    if dt is None:
        return None
    tz = get_timezone()
    if tz is None:
        return dt
    reference = dt
    if getattr(dt, "tzinfo", None) is None:
        reference = dt.replace(tzinfo=ZoneInfo("UTC") if ZoneInfo else None)
    converted = reference.astimezone(tz)
    return converted if aware else converted.replace(tzinfo=None)


def apply_timezone_settings():
    settings = get_settings()
    tz_name = settings.APP_TIMEZONE or _DEFAULT_TZ
    os.environ["TZ"] = tz_name
    try:
        time.tzset()
    except AttributeError:  # Windows compatibility
        logger.debug("time.tzset not available on this platform; skipping")
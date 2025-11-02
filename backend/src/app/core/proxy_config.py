"""Proxy configuration helper.

Scheme A: environment variables

- PROXY_<KEY>_URL for each proxy channel, e.g. PROXY_PROXY1_URL
- PROXY_SERVICE_MAP mapping like: gemini:proxy1,fishaudio:proxy2

get_proxy_for_service(service_name) -> Optional[dict]
returns {'http': url, 'https': url} or None
"""
from __future__ import annotations

import os
from typing import Dict, Optional
from urllib.parse import urlparse


def _parse_service_map(value: Optional[str]) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    if not value:
        return mapping
    for part in value.split(','):
        part = part.strip()
        if not part:
            continue
        if ':' in part:
            svc, key = part.split(':', 1)
            mapping[svc.strip()] = key.strip().lower()
    return mapping


def _load_proxy_channels_from_env() -> Dict[str, str]:
    channels: Dict[str, str] = {}
    for name, val in os.environ.items():
        if not name.startswith('PROXY_') or not name.endswith('_URL'):
            continue
        key = name[len('PROXY_'):-len('_URL')].lower()  # PROXY_PROXY1_URL -> proxy1
        if val:
            channels[key] = val
    return channels


def _host_matches_no_proxy(host: str, no_proxy: Optional[str]) -> bool:
    if not no_proxy:
        return False
    host = host.lower()
    parts = [p.strip().lower() for p in no_proxy.split(',') if p.strip()]
    for p in parts:
        if p == '*':
            return True
        if p.startswith('.') and host.endswith(p):
            return True
        if p.endswith('*') and host.startswith(p[:-1]):
            return True
        if p.startswith('*') and host.endswith(p[1:]):
            return True
        if p == host:
            return True
        # support simple prefix like 192.168.*
        if p.endswith('.*'):
            if host.startswith(p[:-2]):
                return True
    return False


def get_proxy_for_service(service_name: str, target_url: Optional[str] = None) -> Optional[Dict[str, str]]:
    """Return proxies dict for the given service name, or None.

    Order:
      1. PROXY_SERVICE_MAP mapping -> PROXY_<key>_URL
      2. fallback to global HTTP_PROXY/HTTPS_PROXY
      3. None

    If target_url is provided and matches NO_PROXY, returns None.
    """
    # NO_PROXY check
    no_proxy = os.environ.get('NO_PROXY') or os.environ.get('no_proxy')
    if target_url and no_proxy:
        try:
            parsed = urlparse(target_url)
            hostname = parsed.hostname or ''
            if hostname and _host_matches_no_proxy(hostname, no_proxy):
                return None
        except Exception:
            pass

    service_map = _parse_service_map(os.environ.get('PROXY_SERVICE_MAP'))
    channels = _load_proxy_channels_from_env()

    # Enforce explicit mapping: if service not listed in PROXY_SERVICE_MAP -> do NOT use proxy
    if service_name not in service_map:
        return None

    # service is explicitly mapped; try to resolve mapped channel
    key = service_map.get(service_name)
    if key:
        url = channels.get(key)
        if url:
            return {'http': url, 'https': url}

    # Mapped channel missing or misspelled: fall back to global env if available
    http = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
    https = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
    if http or https:
        proxies: Dict[str, str] = {}
        if http:
            proxies['http'] = http
        if https:
            proxies['https'] = https
        return proxies

    # No proxy available
    return None


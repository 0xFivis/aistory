"""Probe script: load backend/.env into process env and print proxy resolution
Run from project root (PowerShell):
  $env:PYTHONPATH=(Resolve-Path .\backend\src).Path; python .\backend\scripts\probe_proxy.py
"""
import os
from pathlib import Path

# Load .env if exists (conservative: do not overwrite existing vars)
env_path = Path(__file__).resolve().parent.parent / '.env'
if env_path.exists():
    for raw in env_path.read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        if '=' in line:
            k, v = line.split('=', 1)
            k = k.strip()
            v = v.strip()
            if k and os.environ.get(k) is None:
                os.environ[k] = v

print('ENV summary:')
for k in ('DATABASE_URL','HTTP_PROXY','http_proxy','HTTPS_PROXY','https_proxy','PROXY_SERVICE_MAP','PROXY_PROXY1_URL','PROXY_PROXY2_URL','NO_PROXY'):
    print(f"{k} = {os.environ.get(k)!r}")

# Import and show proxy resolution
try:
    from app.core.proxy_config import get_proxy_for_service
    print('\nget_proxy_for_service outputs:')
    for svc in ('gemini','fishaudio'):
        print(svc, '->', get_proxy_for_service(svc))
except Exception as exc:
    print('\nERROR importing proxy helper:', exc)

# Quick test: perform a requests GET to httpbin.org if requests is available
try:
    import requests
    print('\nPerforming a quick requests.get to http://httpbin.org/get (timeout=6)')
    r = requests.get('http://httpbin.org/get', timeout=6)
    print('status', r.status_code)
    print('origin (httpbin):', r.json().get('origin'))
except Exception as exc:
    print('\nrequests test skipped or failed:', exc)

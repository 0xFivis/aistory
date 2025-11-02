#!/usr/bin/env bash
set -euo pipefail

APP="app.main:app"
LISTEN_ADDRESS=""
PORT=""
LOG_LEVEL="info"
RELOAD=0
WORKERS=1
VENV=".venv"
EXTRA_ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --app)
            APP="$2"
            shift 2
            ;;
        --host)
            LISTEN_ADDRESS="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --log-level)
            LOG_LEVEL="$2"
            shift 2
            ;;
        --reload)
            RELOAD=1
            shift
            ;;
        --workers)
            WORKERS="$2"
            shift 2
            ;;
        --venv)
            VENV="$2"
            shift 2
            ;;
        --)
            shift
            EXTRA_ARGS+=("$@")
            break
            ;;
        *)
            EXTRA_ARGS+=("$1")
            shift
            ;;
    esac
done

SCRIPT_DIR=$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)
BACKEND_SRC="$SCRIPT_DIR/src"

if [[ -n "$VENV" ]]; then
    if [[ "$VENV" = /* ]]; then
        VENV_PATH="$VENV"
    else
        VENV_PATH="$SCRIPT_DIR/$VENV"
    fi
    if [[ -f "$VENV_PATH/bin/activate" ]]; then
        # shellcheck disable=SC1090
        source "$VENV_PATH/bin/activate"
    else
        echo "[WARN] Virtualenv not found at $VENV_PATH, continuing without activation" >&2
    fi
fi

export PYTHONPATH="$BACKEND_SRC${PYTHONPATH:+:$PYTHONPATH}"

if ! command -v python >/dev/null 2>&1; then
    echo "[ERROR] python command not found. Please ensure virtualenv is activated." >&2
    exit 1
fi

if [[ -z "$LISTEN_ADDRESS" || -z "$PORT" ]]; then
    SETTINGS_JSON=$(python <<'PY' || true)
import json
from app.config.settings import get_settings

settings = get_settings()
print(json.dumps({
    "host": settings.API_HOST or "",
    "port": settings.API_PORT or 0
}))
PY
    if [[ -n "$SETTINGS_JSON" ]]; then
        HOST_FROM_ENV=$(python -c 'import json,sys; data=json.loads(sys.stdin.read()); print(data.get("host",""))' <<<"$SETTINGS_JSON")
        PORT_FROM_ENV=$(python -c 'import json,sys; data=json.loads(sys.stdin.read()); print(data.get("port",0))' <<<"$SETTINGS_JSON")
        if [[ -z "$LISTEN_ADDRESS" && -n "$HOST_FROM_ENV" ]]; then
            LISTEN_ADDRESS="$HOST_FROM_ENV"
        fi
        if [[ -z "$PORT" && "$PORT_FROM_ENV" != "0" ]]; then
            PORT="$PORT_FROM_ENV"
        fi
    fi
fi

if [[ -z "$LISTEN_ADDRESS" ]]; then
    LISTEN_ADDRESS="127.0.0.1"
fi
if [[ -z "$PORT" ]]; then
    PORT="8000"
fi

UVICORN_ARGS=("-m" "uvicorn" "$APP" "--host" "$LISTEN_ADDRESS" "--port" "$PORT" "--log-level" "$LOG_LEVEL")

if [[ "$RELOAD" -eq 1 ]]; then
    UVICORN_ARGS+=("--reload")
fi
if [[ "$WORKERS" -gt 1 ]]; then
    UVICORN_ARGS+=("--workers" "$WORKERS")
fi
if [[ ${#EXTRA_ARGS[@]} -gt 0 ]]; then
    UVICORN_ARGS+=("${EXTRA_ARGS[@]}")
fi

echo "[INFO] Starting Uvicorn"
echo "       App:       $APP"
echo "       Host:      $LISTEN_ADDRESS"
echo "       Port:      $PORT"
echo "       Log level: $LOG_LEVEL"
if [[ "$RELOAD" -eq 1 ]]; then
    echo "       Reload:   enabled"
fi
if [[ "$WORKERS" -gt 1 ]]; then
    echo "       Workers:  $WORKERS"
fi

exec python "${UVICORN_ARGS[@]}"

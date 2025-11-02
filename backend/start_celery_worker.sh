#!/usr/bin/env bash
set -euo pipefail

CONCURRENCY=4
QUEUE="default"
LOG_LEVEL="debug"
POOL="threads"
VENV=".venv"
EXTRA_ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --concurrency)
            CONCURRENCY="$2"
            shift 2
            ;;
        --queue)
            QUEUE="$2"
            shift 2
            ;;
        --log-level)
            LOG_LEVEL="$2"
            shift 2
            ;;
        --pool)
            POOL="$2"
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

CELERY_ARGS=("-m" "celery" "-A" "app.celery_app.celery_app" "worker" "--pool" "$POOL" "--concurrency" "$CONCURRENCY" "--loglevel" "$LOG_LEVEL" "-Q" "$QUEUE")

if [[ ${#EXTRA_ARGS[@]} -gt 0 ]]; then
    CELERY_ARGS+=("${EXTRA_ARGS[@]}")
fi

echo "[INFO] Starting Celery worker"
echo "       Pool:        $POOL"
echo "       Concurrency: $CONCURRENCY"
echo "       Queue:       $QUEUE"
echo "       Log level:   $LOG_LEVEL"

exec python "${CELERY_ARGS[@]}"

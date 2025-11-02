#!/usr/bin/env bash
set -euo pipefail

MODE="dev"
HOST="0.0.0.0"
PORT="5173"
PACKAGE_MANAGER="npm"
EXTRA_ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --mode)
            MODE="$2"
            shift 2
            ;;
        --host)
            HOST="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --pm)
            PACKAGE_MANAGER="$2"
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
cd "$SCRIPT_DIR"

if ! command -v node >/dev/null 2>&1; then
    echo "[ERROR] node command not found. Please install Node.js (>=18)." >&2
    exit 1
fi
if ! command -v "$PACKAGE_MANAGER" >/dev/null 2>&1; then
    echo "[ERROR] Package manager '$PACKAGE_MANAGER' not found. Install it or switch with --pm." >&2
    exit 1
fi

if [[ ! -d node_modules ]]; then
    echo "[INFO] node_modules missing, installing dependencies via $PACKAGE_MANAGER install"
    "$PACKAGE_MANAGER" install
fi

case "$MODE" in
    dev)
        echo "[INFO] Starting Vite dev server on $HOST:$PORT"
        exec "$PACKAGE_MANAGER" run dev -- --host "$HOST" --port "$PORT" "${EXTRA_ARGS[@]}"
        ;;
    build)
        echo "[INFO] Building frontend"
        exec "$PACKAGE_MANAGER" run build "${EXTRA_ARGS[@]}"
        ;;
    preview)
        echo "[INFO] Starting Vite preview server on $HOST:$PORT"
        exec "$PACKAGE_MANAGER" run preview -- --host "$HOST" --port "$PORT" "${EXTRA_ARGS[@]}"
        ;;
    *)
        echo "[ERROR] Unsupported mode '$MODE'. Use dev|build|preview." >&2
        exit 1
        ;;
esac

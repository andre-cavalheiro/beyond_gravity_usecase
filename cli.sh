#!/usr/bin/env bash
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR/api"

PYTHON_BIN="${PYTHON:-python}"
export PYTHONPATH="src${PYTHONPATH:+:$PYTHONPATH}"

exec "$PYTHON_BIN" -m fury_api.scripts.cli "$@"

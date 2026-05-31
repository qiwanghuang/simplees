#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [[ -n "${PYTHON_BIN:-}" ]]; then
  PYTHON="$PYTHON_BIN"
elif [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  PYTHON="$ROOT_DIR/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="python3"
else
  echo "Python is required, but neither .venv/bin/python nor python3 was found." >&2
  exit 1
fi

echo "Using Python: $PYTHON"

if [[ "${INSTALL_DEPS:-0}" == "1" ]]; then
  echo "Installing dependencies from requirements.txt..."
  "$PYTHON" -m pip install -r requirements.txt
fi

if ! "$PYTHON" - <<'PY' >/dev/null 2>&1
import fastapi
import uvicorn
import elasticsearch
import pydantic
import dotenv
import sqlalchemy
import pymysql
import canal.client
import google.protobuf
PY
then
  echo "Project dependencies are missing." >&2
  echo "Run: $PYTHON -m pip install -r requirements.txt" >&2
  echo "Or start with: INSTALL_DEPS=1 ./start.sh" >&2
  exit 1
fi

echo "Initializing database schema..."
"$PYTHON" -m app.init_db

echo "Seeding sample data..."
"$PYTHON" -m app.seed_data

echo "Skipping automatic ES sync on API startup."
echo "Run full ES rebuild manually with: $PYTHON -m app.es_sync"
echo "Run Canal incremental sync with: $PYTHON -m app.canal_consumer"

read -r APP_HOST APP_PORT < <("$PYTHON" - <<'PY'
from app.config import settings

print(settings.app_host, settings.app_port)
PY
)

UVICORN_ARGS=(main:app --host "$APP_HOST" --port "$APP_PORT")

if [[ "${RELOAD:-1}" == "1" ]]; then
  UVICORN_ARGS+=(--reload)
fi

echo "Starting simplees at http://$APP_HOST:$APP_PORT"
exec "$PYTHON" -m uvicorn "${UVICORN_ARGS[@]}" "$@"

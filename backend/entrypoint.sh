#!/bin/sh
set -e

cd /backend

echo "Running migrations..."
uv run alembic revision --autogenerate
uv run alembic upgrade head

echo "Starting API..."
exec uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
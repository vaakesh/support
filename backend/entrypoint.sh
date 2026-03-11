#!/bin/sh
set -e

CERT_DIR="/backend/app/certs"
PRIVATE_KEY="$CERT_DIR/jwt-private.pem"
PUBLIC_KEY="$CERT_DIR/jwt-public.pem"

mkdir -p "$CERT_DIR"
uv run openssl genpkey -algorithm RSA -out "$PRIVATE_KEY" -pkeyopt rsa_keygen_bits:2048
uv run openssl rsa -pubout -in "$PRIVATE_KEY" -out "$PUBLIC_KEY"

cd /backend
echo "Running migrations..."
uv run alembic upgrade head

echo "Starting API..."
exec uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
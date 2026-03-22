#!/bin/sh
set -e

CERT_DIR="/backend/certs"
PRIVATE_KEY="$CERT_DIR/jwt-private.pem"
PUBLIC_KEY="$CERT_DIR/jwt-public.pem"

[ -f "$PRIVATE_KEY" ] || { echo "Missing private key: $PRIVATE_KEY"; exit 1; }
[ -f "$PUBLIC_KEY" ] || { echo "Missing public key: $PUBLIC_KEY"; exit 1; }


cd /backend
echo "Running migrations..."
uv run alembic upgrade head

echo "Starting API..."
exec uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
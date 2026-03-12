#!/bin/sh
set -e

CERT_DIR="/backend/app/certs"
PRIVATE_KEY="$CERT_DIR/jwt-private.pem"
PUBLIC_KEY="$CERT_DIR/jwt-public.pem"

mkdir -p "$CERT_DIR"
if [ ! -f "$PRIVATE_KEY" ]; then
    echo "Generating private/public key pair..."
    uv run openssl genpkey -algorithm RSA -out "$PRIVATE_KEY" -pkeyopt rsa_keygen_bits:2048
    uv run openssl rsa -pubout -in "$PRIVATE_KEY" -out "$PUBLIC_KEY"
elif [ ! -f "$PUBLIC_KEY" ]; then
    echo "Generating public key from existing private key..."
    uv run openssl rsa -pubout -in "$PRIVATE_KEY" -out "$PUBLIC_KEY"
else
    echo "Keys already exist, skipping."
fi

cd /backend
echo "Running migrations..."
uv run alembic upgrade head

echo "Starting API..."
exec uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
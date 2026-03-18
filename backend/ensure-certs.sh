#!/usr/bin/env bash
set -euo pipefail

CERT_DIR="./backend/certs"
PRIVATE_KEY="$CERT_DIR/jwt-private.pem"
PUBLIC_KEY="$CERT_DIR/jwt-public.pem"

mkdir -p "$CERT_DIR"

if [[ ! -f "$PRIVATE_KEY" ]]; then
    echo "Generating private/public key pair..."
    openssl genpkey -algorithm RSA -out "$PRIVATE_KEY" -pkeyopt rsa_keygen_bits:2048
    openssl rsa -pubout -in "$PRIVATE_KEY" -out "$PUBLIC_KEY"
elif [[ ! -f "$PUBLIC_KEY" ]]; then
    echo "Generating public key from existing private key..."
    openssl rsa -pubout -in "$PRIVATE_KEY" -out "$PUBLIC_KEY"
else
    echo "Keys already exist, skipping."
fi
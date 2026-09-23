#!/usr/bin/env bash
# Dev-only self-signed TLS cert for nginx (see infra/nginx/nginx.conf).
# Browsers will show a certificate warning — expected for local dev.
# Swap infra/nginx/certs/*.pem for a real certificate before any real
# deployment.
set -euo pipefail

CERT_DIR="$(dirname "$0")/certs"
mkdir -p "$CERT_DIR"

openssl req -x509 -nodes -days 365 \
  -newkey rsa:2048 \
  -keyout "$CERT_DIR/privkey.pem" \
  -out "$CERT_DIR/fullchain.pem" \
  -subj "/C=IN/ST=Gujarat/L=Gandhinagar/O=Sentinel Grid Dev/CN=localhost"

echo "Generated $CERT_DIR/fullchain.pem and $CERT_DIR/privkey.pem"

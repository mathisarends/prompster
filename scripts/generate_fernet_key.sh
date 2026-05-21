#!/usr/bin/env bash
set -euo pipefail

KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

echo "Generated Fernet key:"
echo ""
echo "SPOTIFY_TOKEN_ENCRYPTION_KEY=$KEY"

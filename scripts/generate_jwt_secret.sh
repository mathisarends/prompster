#!/usr/bin/env bash
set -euo pipefail

SECRET=$(python -c "import secrets; print(secrets.token_hex(32))")

echo "Generated JWT secret:"
echo ""
echo "JWT_SECRET=$SECRET"

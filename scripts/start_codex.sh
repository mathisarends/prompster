#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
cd -- "${ROOT_DIR}"

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  echo "Usage: bash scripts/start_codex.sh [docker compose up options]"
  echo "Starts the stack with compose.codex.yml; pass -d to run in the background."
  exit 0
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose v2 is required. Install Docker with the Compose plugin." >&2
  exit 1
fi

compose() {
  MSYS_NO_PATHCONV=1 docker compose "$@"
}

# Let Compose parse .env, including quoting, interpolation and shell precedence.
# Use the base file here because the override requires CODEX_AUTH_DIR already.
AUTH_DIR="$(compose -f compose.yml config --environment | sed -n 's/^CODEX_AUTH_DIR=//p' | tr -d '\r')"
AUTH_DIR="${AUTH_DIR:-${CODEX_HOME:-${HOME}/.codex}}"

if [[ ! -d "${AUTH_DIR}" || ! -r "${AUTH_DIR}/auth.json" || ! -f "${AUTH_DIR}/auth.json" ]]; then
  echo "No readable Codex login file found at ${AUTH_DIR}/auth.json." >&2
  echo "Run codex login in the intended Codex home, or set CODEX_AUTH_DIR in .env." >&2
  echo "For file-based credentials: codex -c 'cli_auth_credentials_store=\"file\"' login" >&2
  exit 1
fi

AUTH_DIR="$(cd -- "${AUTH_DIR}" && pwd)"
if command -v cygpath >/dev/null 2>&1; then
  # Docker Desktop needs a native absolute Windows path when using Git Bash.
  AUTH_DIR="$(cygpath -am "${AUTH_DIR}")"
fi
export CODEX_AUTH_DIR="${AUTH_DIR}"

compose -f compose.yml -f compose.codex.yml config --quiet
echo "Starting the Codex stack with credentials from ${CODEX_AUTH_DIR} (read-only)."
compose -f compose.yml -f compose.codex.yml up --build "$@"

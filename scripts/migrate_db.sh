#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
COMPOSE_FILE="${ROOT_DIR}/compose.yml"

if [[ ! -f "${COMPOSE_FILE}" ]]; then
  echo "compose.yml not found at ${COMPOSE_FILE}" >&2
  exit 1
fi

cd "${ROOT_DIR}"

if docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_CMD=(docker-compose)
else
  echo "Neither 'docker compose' nor 'docker-compose' is available." >&2
  exit 1
fi

POSTGRES_USER="${POSTGRES_USER:-prompster}"
POSTGRES_DB="${POSTGRES_DB:-prompster}"

compose() {
  MSYS_NO_PATHCONV=1 "${COMPOSE_CMD[@]}" "$@"
}

echo "[1/5] Starting postgres service..."
compose up -d postgres

echo "[2/5] Waiting for postgres to become ready..."
for _ in $(seq 1 60); do
  if compose exec -T postgres pg_isready -U "${POSTGRES_USER}" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

if ! compose exec -T postgres pg_isready -U "${POSTGRES_USER}" >/dev/null 2>&1; then
  echo "Postgres did not become ready in time." >&2
  exit 1
fi

echo "[3/5] Fixing alembic_version column length (if needed)..."
compose exec -T postgres psql -v ON_ERROR_STOP=1 -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" <<'SQL'
DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'alembic_version'
      AND column_name = 'version_num'
      AND data_type = 'character varying'
      AND character_maximum_length IS NOT NULL
      AND character_maximum_length < 128
  ) THEN
    ALTER TABLE public.alembic_version
      ALTER COLUMN version_num TYPE VARCHAR(128);
  END IF;
END
$$;
SQL

echo "[4/5] Removing stale migrate container (if present)..."
compose rm -sf migrate >/dev/null 2>&1 || true

echo "[5/5] Running alembic migrations..."
compose run --rm --no-deps \
  -v "${ROOT_DIR}/backend/src:/app/backend/src" \
  -v "${ROOT_DIR}/backend/migrations:/app/backend/migrations" \
  migrate alembic -c /app/backend/alembic.ini upgrade head

echo "Done. Database migration completed."

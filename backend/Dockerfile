FROM python:3.14-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install uv

COPY pyproject.toml uv.lock* ./
COPY libs/agent/pyproject.toml libs/agent/README.md* libs/agent/
COPY backend/pyproject.toml backend/README.md* backend/
COPY libs/tokens/pyproject.toml libs/tokens/README.md* libs/tokens/
COPY libs/agent/src libs/agent/src
COPY backend/src backend/src
COPY libs/tokens/src libs/tokens/src

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --package backend

FROM python:3.14-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv

COPY libs/agent/src ./libs/agent/src
COPY backend/src ./backend/src
COPY libs/tokens/src ./libs/tokens/src
COPY backend/alembic.ini ./backend/alembic.ini
COPY backend/migrations ./backend/migrations

ENV PYTHONPATH=/app/backend/src \
    PATH="/app/.venv/bin:$PATH" \
    RELOAD=false

EXPOSE 8000

CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port 8000 \
    $([ \"$RELOAD\" = 'true' ] && echo '--reload --reload-dir /app/backend/src --reload-dir /app/libs/agent/src')"]

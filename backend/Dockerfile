FROM python:3.14-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    libpq-dev \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install uv

COPY pyproject.toml uv.lock* ./
COPY libs/agent/pyproject.toml libs/agent/README.md* libs/agent/
COPY backend/pyproject.toml backend/README.md* backend/
COPY libs/agent/src libs/agent/src
COPY backend/src backend/src

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
COPY backend/pyproject.toml ./backend/pyproject.toml
COPY backend/migrations ./backend/migrations

ENV PYTHONPATH=/app/backend/src \
    PATH="/app/.venv/bin:$PATH" \
    RELOAD=false

EXPOSE 8000

CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port 8000 \
    $([ \"$RELOAD\" = 'true' ] && echo '--reload --reload-dir /app/backend/src --reload-dir /app/libs/agent/src')"]

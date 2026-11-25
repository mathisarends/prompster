# Datenbank-Migrationen (Alembic über fastapi-canon)

## Setup

- Die Datenbank ist eine `fastapi-canon`-Integration (`Database`), erstellt in
  `backend/src/backend/platform/database/di.py`. Die Tabellen meldet das
  Plattform-Feature über `Tables(...)` an; daraus setzt Canon die Metadata für
  Autogenerate und Prüfungen zusammen.
- Migrationen liegen in `backend/migrations/versions`. `backend/migrations/env.py`
  ruft nur `run_alembic_environment()` auf.
- `fastapi-canon db` liest sein Ziel (`backend.main:app`) aus
  `[tool.fastapi-canon.database]` in `backend/pyproject.toml` und die Verbindung
  aus `DB_URI`. Außerhalb von Compose `DB_URI` selbst setzen, z. B.
  `postgresql://<user>:<passwort>@localhost:5432/prompster`.
- Beim Start prüft die App, dass die Datenbank auf dem Stand der Revisionen ist,
  und startet sonst nicht. Migrationen laufen deshalb immer vor dem Backend.

## Migrationen ausführen

Empfohlen (Compose, inkl. Retry/Recovery):

1. docker compose up --build migrate
2. Prüfen, ob erfolgreich: docker compose ps
3. Danach normal starten: docker compose up --build backend

Oder alles zusammen starten (backend wartet auf erfolgreiche Migration):

1. docker compose up --build

## Neue Migration erstellen

1. Modell ändern (z. B. SQLModel-Entity). Eine neue Tabelle zusätzlich in
   `DATABASE_TABLES` eintragen.
2. Revision erzeugen:
   uv run --package backend fastapi-canon db --config backend/pyproject.toml revision --autogenerate -m "describe_change"
3. Generierte Datei prüfen/aufräumen. Die Revisions-ID im bisherigen Schema
   (`0041_describe_change`) im Dateinamen, in `revision` und `down_revision`
   nachziehen.
4. Migration anwenden:
   uv run --package backend fastapi-canon db --config backend/pyproject.toml upgrade head

## Recovery bei Fehlern

- Der Compose-Service migrate hat einen Retry-Loop (20 Versuche, 3s Abstand).
- Bei temporären DB-Problemen startet er automatisch erneut (restart: on-failure).
- Nach Fix erneut ausführen:
  docker compose up --build migrate

Häufiger Fehler:

- InvalidPasswordError: DB_URI-Credentials passen nicht zu POSTGRES_USER/POSTGRES_PASSWORD.
- Standardmäßig wird DB_URI im compose.yml bereits aus POSTGRES_* gebaut. Falls du DB_URI explizit setzt, muss es exakt zu den Postgres-Variablen passen.

## Nützliche Befehle

Alle mit dem Präfix `uv run --package backend fastapi-canon db --config backend/pyproject.toml`:

- Auf letzte Version: `upgrade head`
- Auf eine bestimmte Revision zurück: `downgrade <revision>`
- Stand und Drift prüfen (Revisionen aktuell, Modelle = Schema): `check`

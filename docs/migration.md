# Datenbank-Migrationen (Alembic)

## Setup

- Docker Desktop / Docker Engine muss laufen.
- Migrationen liegen in backend/migrations/versions.
- Alembic-Konfig liegt in backend/alembic.ini.
- Modelle werden in backend/migrations/env.py geladen und als Metadata für Autogenerate verwendet.

## Erste Migration ausführen

Empfohlen (Compose, inkl. Retry/Recovery):

1. docker compose up --build migrate
2. Prüfen, ob erfolgreich: docker compose ps
3. Danach normal starten: docker compose up --build backend

Oder alles zusammen starten (backend wartet auf erfolgreiche Migration):

1. docker compose up --build

## Neue Migration erstellen

1. Modell ändern (z. B. SQLModel-Entity)
2. Revision erzeugen:
   cd backend && alembic revision --autogenerate -m "describe_change"
3. Generierte Datei prüfen/aufräumen
4. Migration anwenden:
   cd backend && alembic upgrade head

## Recovery bei Fehlern

- Der Compose-Service migrate hat einen Retry-Loop (20 Versuche, 3s Abstand).
- Bei temporären DB-Problemen startet er automatisch erneut (restart: on-failure).
- Nach Fix erneut ausführen:
  docker compose up --build migrate

Häufiger Fehler:

- InvalidPasswordError: DB_URI-Credentials passen nicht zu POSTGRES_USER/POSTGRES_PASSWORD.
- Standardmäßig wird DB*URI im compose.yml bereits aus POSTGRES*\* gebaut. Falls du DB_URI explizit setzt, muss es exakt zu den Postgres-Variablen passen.

## Nützliche Befehle

- Aktueller Stand: cd backend && alembic current
- Historie: cd backend && alembic history
- Auf letzte Version: cd backend && alembic upgrade head
- Einen Schritt zurück: cd backend && alembic downgrade -1

# Session Listing, Search & ORM Refactor

## Ziel

Frontend-Anforderungen:

1. **Sidebar „Verlauf"** — Liste aller Sessions des Users, sortiert nach letzter Aktivität, mit Gruppierung (Heute / Gestern / Letzte 7 Tage / Älter). Pro Eintrag werden nur `id`, `title` und ein Zeitstempel gebraucht.
2. **Search-Dialog (Cmd+K)** — Fuzzy-/Title-Search über die Sessions des Users. Gleiche Felder wie oben.
3. **Detail-Ansicht** — Volles Aggregate inkl. Messages, Tool-Calls, Follow-Ups, Playlist (heutiges Verhalten von `GET /sessions/{id}`).

Aktuelles Problem: Es gibt keinen Endpoint für (1) und (2). `GET /sessions/{id}` lädt zwar das volle Aggregat, aber das ORM speichert `messages` und `playlist` als JSON-Blobs in der `sessions`-Tabelle. Damit ist „leichtgewichtig laden" nicht möglich — jede Query zieht den kompletten Blob mit. Für die Listenansicht ist das verschwendet, und die JSON-Spalten machen Suche (LIKE/Volltext) auf Messages und Playlists kostspielig und schwer zu indizieren.

## Leitprinzipien

- **CQRS-Light**: Schreibseite arbeitet weiter über das `Session`-Aggregate. Leseseite für die Liste/Suche ist ein eigener Read-Model-Pfad, der nicht das ganze Aggregat instanziiert.
- **DDD-Grenzen sauber**: Domain bleibt persistence-agnostisch. Die Aufteilung in mehrere Tabellen ist eine reine Infrastructure-Entscheidung. Das Aggregate `Session` bleibt nach außen unverändert.
- **Aggregate Boundary**: `Session` bleibt der Aggregate Root und umfasst weiterhin `messages` und (eine) `playlist`. Beides sind Entities/Value-Objects innerhalb der Aggregate-Grenze, nicht eigene Aggregates — Begründung unten.
- **Keine Premature Abstraction**: Tool-Call- und Follow-Up-Gruppen bleiben weiterhin JSON-Spalten **auf der Message-Zeile** (sie sind 1:1 an eine Message gebunden, werden nie isoliert abgefragt, und eigene Tabellen wären jetzt Overkill).

## Sollte Playlist ein eigenes Aggregate sein?

Empfehlung: **Nein, weiterhin Teil des Session-Aggregates**. Gründe:

- Beziehung ist heute strikt 1:0..1 (eine Session hat höchstens eine Playlist) und die Tracks werden nur im Kontext der Session manipuliert.
- Es gibt keinen Use-Case, der Playlists ohne ihre Session lädt, exportiert oder mit anderen Sessions teilt.
- Konsistenzregeln (z.B. „nur der Owner der Session darf Tracks ändern") leben sauber im Session-Aggregate.

Wenn später Use-Cases auftauchen wie „Playlist standalone in Spotify exportieren / mehrfach verwenden / mit anderem User teilen", kann Playlist zu einem eigenen Aggregate werden. Bis dahin: separate **Tabellen** (Persistence-Entscheidung), aber **ein Aggregate** (Domain-Entscheidung).

## Ziel-Schema

```
sessions
  id                UUID PK
  owner_id          UUID NOT NULL, INDEX
  title             TEXT NOT NULL
  created_at        TIMESTAMPTZ NOT NULL
  last_activity_at  TIMESTAMPTZ NOT NULL          -- denormalisiert, siehe unten
  INDEX (owner_id, last_activity_at DESC)
  INDEX gin/trgm on title                          -- für Title-Search (Postgres pg_trgm)

session_messages
  id                UUID PK
  session_id        UUID NOT NULL, FK -> sessions.id ON DELETE CASCADE
  position          INT  NOT NULL                  -- stabile Reihenfolge
  role              TEXT NOT NULL                  -- 'user' | 'assistant'
  content           TEXT NOT NULL
  tool_call_group   JSONB NULL                     -- bleibt als Blob, 1:1 mit Message
  follow_up_group   JSONB NULL                     -- bleibt als Blob, 1:1 mit Message
  created_at        TIMESTAMPTZ NOT NULL
  INDEX (session_id, position)

session_playlists
  id                UUID PK
  session_id        UUID NOT NULL UNIQUE, FK -> sessions.id ON DELETE CASCADE
  name              TEXT NULL
  created_at        TIMESTAMPTZ NOT NULL

playlist_tracks
  id                UUID PK
  playlist_id       UUID NOT NULL, FK -> session_playlists.id ON DELETE CASCADE
  position          INT  NOT NULL
  title             TEXT NOT NULL
  artist            TEXT NOT NULL
  year              INT  NULL
  cover_url         TEXT NULL
  created_at        TIMESTAMPTZ NOT NULL
  INDEX (playlist_id, position)
```

### `last_activity_at` denormalisiert

Damit die Sidebar/Search ohne JOIN auf Messages sortieren kann, halten wir `last_activity_at` auf der Session-Zeile. Wird gesetzt:

- bei Create auf `created_at`
- in `SessionRepository.save(...)` (oder einer dedizierten `touch`-Methode) immer dann, wenn eine Message hinzugefügt wurde

Trade-off: minimaler Schreib-Overhead vs. JOIN-freie, indizierte Sortierung der Liste. Lohnt sich.

## Domain-Änderungen

Praktisch **keine** in der Public API von `Session` — das ist der Punkt von DDD: die Persistenz ändert sich, das Aggregate bleibt stabil.

Mögliche Mini-Anpassung: Eine `touch()`-Methode oder ein internes Flag, das das Repository in `save(...)` ausliest, um `last_activity_at` zu aktualisieren. Alternativ regelt das das Repository selbst, indem es bei `save` immer `last_activity_at = now()` setzt, sobald sich `messages` geändert haben. → Bevorzugt: Repository macht das implizit, Domain bleibt davon unberührt.

## Read Model für Listing/Search

Eigener Query-Pfad, **nicht** über `SessionRepository.get_by_id`. So bleibt das Aggregate-Repository fokussiert.

```
backend/features/session/
  application/
    queries/
      list_sessions.py         # ListSessionsHandler
      search_sessions.py       # SearchSessionsHandler
    ports/
      session_summary_query.py # SessionSummaryQuery (read-model port)
  infrastructure/
    session_summary_query.py   # SqlSessionSummaryQuery
```

### Read-Model-Shape

```python
@dataclass(frozen=True)
class SessionSummary:
    id: UUID
    title: str
    created_at: datetime
    last_activity_at: datetime
```

Bewusst flach. Kein `messages`, kein `playlist`, keine Aggregate-Methoden — das ist explizit ein DTO der Leseseite, kein Domain-Objekt.

### Port

```python
class SessionSummaryQuery(ABC):
    @abstractmethod
    async def list_for_owner(
        self, *, owner_id: UUID, limit: int, offset: int
    ) -> list[SessionSummary]: ...

    @abstractmethod
    async def search_for_owner(
        self, *, owner_id: UUID, query: str, limit: int
    ) -> list[SessionSummary]: ...
```

Die SQL-Implementierung selektiert nur die 4 Spalten aus `sessions` — kein JOIN, kein JSON-Parsing.

### Suche

Pragmatischer Start: `ILIKE '%query%'` auf `title`, indiziert via `pg_trgm`. Falls später Volltextsuche auf Messages gewünscht ist, wird das ein separater Schritt mit eigener Infrastruktur (tsvector / externer Suchindex) — **nicht** Teil dieses Plans.

## Presentation: Endpoints

| Method | Path                  | Zweck                          | Response                          |
|--------|-----------------------|--------------------------------|-----------------------------------|
| GET    | `/sessions`           | Liste (Sidebar)                | `SessionSummaryListResponse`      |
| GET    | `/sessions/search?q=` | Title-Search (Search-Dialog)   | `SessionSummaryListResponse`      |
| GET    | `/sessions/{id}`      | Detail (unverändert)           | `SessionResponse` (volles Aggregat)|
| POST   | `/sessions`           | Create (unverändert)           | `SessionResponse`                 |
| PATCH  | `/sessions/{id}`      | Update Title (unverändert)     | `SessionResponse`                 |
| DELETE | `/sessions/{id}`      | Delete (unverändert)           | 204                               |
| POST   | `/sessions/{id}/messages` | Send Message (unverändert) | StreamingResponse                 |

### Alternative: ein Endpoint mit Query-Param

`GET /sessions?q=&limit=&offset=` — `q` optional, ohne `q` ist es Liste, mit `q` Suche. Sauberer REST-Stil, ein Operation, weniger Routes. **Empfehlung: diese Variante**, weil der Response-Typ identisch ist und sich Frontend/Generated-Client einfacher anfühlt.

### Schema

```python
class SessionSummaryResponse(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    last_activity_at: datetime

class SessionSummaryListResponse(BaseModel):
    items: list[SessionSummaryResponse]
```

Gruppierung (Heute / Gestern / Letzte 7 Tage / Älter) bleibt **Frontend-Concern**. Backend liefert nur Zeitstempel.

## Migration

Eine Alembic-Migration in mehreren Schritten:

1. Neue Tabellen `session_messages`, `session_playlists`, `playlist_tracks` anlegen.
2. Spalte `last_activity_at` auf `sessions` ergänzen (initial = `created_at`).
3. Daten umziehen: für jede Session JSON `messages`/`playlist` auspacken → Inserts in die neuen Tabellen. `last_activity_at = max(created_at, messages[-1].created_at)`.
4. Indizes anlegen (`pg_trgm` Extension + GIN-Index auf `sessions.title`).
5. JSON-Spalten `messages`, `playlist` aus `sessions` entfernen.

Schritt 3 als Datenmigration im Migrationsskript, falls Volumen klein. Bei größerem Volumen aufteilen (Schema-Migration zuerst, Daten in separatem Job, Drop danach).

## Repository-Anpassung

`SqlSessionRepository`:

- `_to_domain(orm)` / `_to_orm(domain)` aktualisieren, sodass `messages` über `session.messages.append(...)` und `playlist` über die Relation gelesen/geschrieben werden statt aus JSON.
- `get_by_id` lädt mit `selectinload(SessionEntity.messages, SessionEntity.playlist.tracks)` — ein Round-Trip, alles dabei.
- `save` synchronisiert Message-Liste, Playlist und Tracks (Diff oder „delete-and-reinsert" auf Aggregate-Wurzel — pragmatisch reicht erstmal Letzteres, weil Sessions selten sehr lang sind; falls Performance ein Thema wird, gezielt diffen).
- `save` setzt `last_activity_at = now()`, wenn die Message-Liste sich geändert hat (Hash/Count-Vergleich gegen die DB-Zeile reicht).

`SqlSessionSummaryQuery` (neu):

- Reines `SELECT id, title, created_at, last_activity_at FROM sessions WHERE owner_id = :owner_id [AND title ILIKE :q] ORDER BY last_activity_at DESC LIMIT/OFFSET`.
- Mapping → `SessionSummary`-Dataclass.

## Frontend-Anpassung (Skizze)

- Orval-Client neu generieren nach Backend-Änderung.
- `navigation-sidebar.tsx`: `mockChats` entfernen, stattdessen `useListSessions()` (oder wie der generierte Hook heißt). Gruppieren clientseitig nach `last_activity_at` in `Heute/Gestern/Letzte 7 Tage/Älter`.
- `chat-search-dialog.tsx`: debounced Query gegen denselben Endpoint mit `q=...`.
- `mockChats.ts` löschen, sobald nichts mehr darauf zeigt.

## Reihenfolge der Umsetzung

1. **Schema + Migration** (Tabellen, `last_activity_at`, Indizes, Daten-Umzug).
2. **Repository-Umbau** auf relationale Mapper — Detail-Endpoint und alle Commands müssen grün bleiben. Tests anpassen.
3. **Read-Model-Pfad** (Port, SQL-Implementierung, Handler, Endpoint, Schema).
4. **Frontend** umstellen, Orval regenerieren, Mock-Daten entfernen.
5. **pg_trgm + Title-Index** (kann auch in Schritt 1, je nach Migrationsstrategie).

## Was bewusst NICHT Teil dieses Plans ist

- Volltextsuche über Message-Inhalte (eigener späterer Schritt mit `tsvector` o.ä.).
- Playlist als eigenes Aggregate (erst wenn Standalone-Use-Cases kommen).
- Tool-Calls / Follow-Ups in eigene Tabellen normalisieren (kein Query-Bedarf, der das rechtfertigt).
- Paging-Strategie über Cursor — `limit/offset` reicht für den erwarteten Datenumfang.
- Soft-Delete / Archivierung.

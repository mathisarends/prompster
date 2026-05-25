# Workspace Event Persistence — Implementation Plan

## Ziel

Wenn der User über die REST-API Tracks pinnt, unpinnt, hinzufügt oder entfernt, ist der Agent davon abgeschnitten — er hat einen veralteten Snapshot aus seinem letzten Turn im Kontext. Wir bauen die Datengrundlage, um jede manuelle User-Mutation als `WorkspaceEvent` strukturiert zu persistieren. Der Event-Log hat einen `consumed: bool`-Flag, sodass später (in einem Folge-Plan) entschieden werden kann, welche Events dem Agent beim nächsten Turn injiziert werden müssen.

**Scope dieses Plans:** Domain, ORM/Migration, Repository-Round-Trip, Application-Service. **NICHT enthalten:** Agent-Injection, Prompt-Bau, Konsumierungs-Trigger im Runner. Optional: ein Debug-Endpoint zum Lesen — aber kein neuer Schreib-Endpoint, Events entstehen ausschließlich als Side-Effect bestehender Track-Endpoints.

---

## Architektur-Entscheidungen

1. **WorkspaceEvent ist Teil des Session-Aggregats** (so wie `Playlist`). Lifecycle hängt am Session, FK-Cascade-Delete. Kein eigenes Aggregat — wir wollen Konsistenz in einem Save.
2. **Append-only Liste auf der Session**, `position`-Spalte erhält Reihenfolge wie bei `user_messages`/`assistant_messages`.
3. **`consumed: bool`** statt Cursor: Einfach zu reasonen, einfach zu queryen, ein Event kann jederzeit als "wieder ungelesen" markiert werden falls wir das mal brauchen.
4. **Quelle der Events = `SessionService` Track-Methoden.** Das sind genau die Pfade, die der manuelle User aufruft (REST `/sessions/{id}/tracks/...`). Wenn der Agent intern Tracks über den `SessionRunner` / Tools verändert, läuft das nicht durch `SessionService` und emittiert daher keine Events. Falls diese Annahme später nicht mehr stimmt, fügen wir ein `source`-Feld hinzu — vorerst lassen wir es weg (YAGNI).
5. **Events werden in `Session` selbst emittiert** (Domain-Logik), nicht im Service. Service ruft `session.add_track(...)`, Session erzeugt sowohl `PlaylistTrack` als auch den `WorkspaceEvent`-Eintrag. Damit ist die Datenkonsistenz garantiert ohne dass jemand "vergisst" das Event zu schreiben.
6. **Snapshot der Track-Daten im Event:** Titel/Artist/URI werden zum Zeitpunkt des Events kopiert. Ein nach dem Event gelöschter Track ist im Log immer noch lesbar (`title: "Bohemian Rhapsody"` — der Agent braucht die menschliche Beschreibung).

---

## Domänenmodell — neue Entität

```
WorkspaceEvent
├── id: UUID
├── event_type: WorkspaceEventType  (TRACK_PINNED | TRACK_UNPINNED | TRACK_ADDED | TRACK_REMOVED)
├── track_id: UUID                  (auch bei REMOVED — der ehemalige Track-ID, kein FK)
├── track_title: str                (Snapshot)
├── track_artist: str               (Snapshot)
├── track_spotify_uri: str | None   (Snapshot, primär relevant bei ADDED)
├── occurred_at: datetime
└── consumed: bool                  (default False)
```

`track_id` ist **kein FK** — bei `TRACK_REMOVED` wäre der referenzierte Row dann weg. Wir speichern die UUID als Wert.

---

## Änderungen (in Reihenfolge)

### 1. Domain Layer

#### 1.1 Neue Datei `backend/src/backend/features/session/domain/entities/workspace_event.py`

```python
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from backend.shared.ddd import Entity


class WorkspaceEventType(StrEnum):
    TRACK_PINNED = "track_pinned"
    TRACK_UNPINNED = "track_unpinned"
    TRACK_ADDED = "track_added"
    TRACK_REMOVED = "track_removed"


class WorkspaceEvent(Entity):
    def __init__(
        self,
        event_type: WorkspaceEventType,
        track_id: UUID,
        track_title: str,
        track_artist: str,
        track_spotify_uri: str | None = None,
        consumed: bool = False,
        id: UUID | None = None,
        created_time: datetime | None = None,
    ) -> None:
        super().__init__(id=id, created_time=created_time)
        self.event_type = event_type
        self.track_id = track_id
        self.track_title = track_title
        self.track_artist = track_artist
        self.track_spotify_uri = track_spotify_uri
        self.consumed = consumed

    @property
    def occurred_at(self) -> datetime:
        return self.created_at

    def mark_consumed(self) -> None:
        self.consumed = True
```

#### 1.2 Exporte erweitern

- `domain/entities/__init__.py`: `WorkspaceEvent`, `WorkspaceEventType` re-exportieren
- `domain/__init__.py`: gleiche zwei Namen in `__all__` aufnehmen

#### 1.3 `domain/session.py` — Session-Aggregat erweitern

- Konstruktor bekommt neuen Parameter `workspace_events: list[WorkspaceEvent] | None = None`, speichert in `self._workspace_events: list[WorkspaceEvent] = workspace_events or []`
- Neue Property:
  ```python
  @property
  def workspace_events(self) -> tuple[WorkspaceEvent, ...]:
      return tuple(self._workspace_events)
  ```
- Neue private Methode `_record_event(event_type, track)` die ein `WorkspaceEvent` aus einem `PlaylistTrack`-Snapshot baut und an `self._workspace_events` anhängt.
- Mutator-Methoden ergänzen:
  - `add_track(...)`: nach dem `playlist.tracks.append(track)` → `self._record_event(TRACK_ADDED, track)`
  - `remove_track(track_id)`: **vor** dem `pop` den Track lesen, dann `self._record_event(TRACK_REMOVED, track)` nach erfolgreichem Pop
  - `pin_track(track_id)`: nach `track.is_pinned = True` → `self._record_event(TRACK_PINNED, track)`. Falls Track schon gepinnt war: **kein** Event (idempotent — verhindert Lärm). Vergleichswert vor der Mutation lesen.
  - `unpin_track(track_id)`: analog, nur falls vorher `is_pinned == True`
- Neue Public-API für Konsum (vorerst nur Reader, kein Writer der Bulk-Konsumiert — das kommt im nächsten Plan):
  ```python
  def unconsumed_workspace_events(self) -> tuple[WorkspaceEvent, ...]:
      return tuple(e for e in self._workspace_events if not e.consumed)
  ```
- `replace_track(...)` emittiert vorerst **kein** Event (das passiert nur im Runner-Pfad, nicht über REST).
- `set_playlist(...)` / `add_tracks(...)` (Bulk vom Runner) emittieren vorerst **kein** Event.

### 2. Infrastructure Layer

#### 2.1 ORM (`backend/src/backend/infrastructure/database/orm.py`)

Neues Model anhängen:

```python
class SessionWorkspaceEventModel(DatabaseEntity, table=True):
    __tablename__ = "session_workspace_events"
    __table_args__ = (
        Index(
            "ix_session_workspace_events_session_position",
            "session_id",
            "position",
        ),
        Index(
            "ix_session_workspace_events_session_consumed",
            "session_id",
            "consumed",
        ),
    )

    session_id: UUID = Field(foreign_key="sessions.id")
    position: int
    event_type: str
    track_id: UUID
    track_title: str
    track_artist: str
    track_spotify_uri: str | None = Field(default=None, max_length=128)
    consumed: bool = Field(
        default=False,
        sa_type=Boolean(),
        sa_column_kwargs={"server_default": text("false")},
    )

    session: SessionModel = Relationship(back_populates="workspace_events")
```

Auf `SessionModel` neue Relationship hinzufügen:

```python
workspace_events: list["SessionWorkspaceEventModel"] = Relationship(
    back_populates="session",
    sa_relationship_kwargs={"cascade": "all, delete-orphan"},
)
```

#### 2.2 Alembic-Migration `backend/migrations/versions/0017_add_session_workspace_events.py`

- `revision = "0017_add_session_workspace_events"`
- `down_revision = "0016_rename_playlist_track_is_locked_to_is_pinned"`
- `upgrade()`:
  - `op.create_table("session_workspace_events", ...)` mit allen Spalten (id PK, created_at server_default now(), session_id FK→sessions.id, position int, event_type varchar, track_id UUID, track_title text, track_artist text, track_spotify_uri varchar(128) nullable, consumed bool server_default false)
  - `op.create_index("ix_session_workspace_events_session_position", "session_workspace_events", ["session_id", "position"])`
  - `op.create_index("ix_session_workspace_events_session_consumed", "session_workspace_events", ["session_id", "consumed"])`
- `downgrade()`: Indexe droppen, Tabelle droppen.

#### 2.3 `SqlSessionRepository` (`infrastructure/repository.py`)

- `_detail_query`: in `.options(...)` zusätzliches `selectinload(SessionModel.workspace_events)` aufnehmen
- `_to_domain`: nach dem Sortieren der `entries`-Liste:
  ```python
  workspace_events = sorted(orm.workspace_events, key=lambda r: r.position)
  domain_events = [self._to_domain_workspace_event(e) for e in workspace_events]
  ```
  und an `Session(...)` als `workspace_events=domain_events` übergeben.
- `_sync_entries` (oder neue parallele Methode `_sync_workspace_events`):
  ```python
  existing = {row.id: row for row in orm.workspace_events if row.id is not None}
  rows = []
  for position, event in enumerate(session.workspace_events):
      row = existing.get(event.id) or SessionWorkspaceEventModel(id=event.id)
      row.session_id = session_id
      row.position = position
      row.event_type = event.event_type.value
      row.track_id = event.track_id
      row.track_title = event.track_title
      row.track_artist = event.track_artist
      row.track_spotify_uri = event.track_spotify_uri
      row.consumed = event.consumed
      row.created_at = event.created_at
      rows.append(row)
  orm.workspace_events = rows
  ```
  Aufruf neben `_sync_entries` in `save(...)` einbauen.
- Neue Helper `_to_domain_workspace_event(row)` analog zu den anderen `_to_domain_*`-Methoden, mappt `WorkspaceEventType(row.event_type)` zurück.
- `_resolve_last_activity_at`: ggf. erweitern um workspace_events einzubeziehen — sonst zeigt eine Pin-Aktion nicht in der Session-Liste. **Entscheidung:** ja, einbeziehen — `last_activity_at` soll alle relevanten Modifikationen widerspiegeln. Loop ergänzen, der über `session.workspace_events` läuft und `created_at` vergleicht.

### 3. Application Layer

Hier ist die Arbeit klein, weil die Event-Emission im Domain-Aggregat passiert. Konkret:

- **Keine** Signatur-Änderung an `SessionService.add_playlist_track / pin_playlist_track / unpin_playlist_track / remove_playlist_track`. Sie rufen weiterhin `session.add_track(...)` etc. und persistieren via `save(session=session)`. Da `Session` jetzt selbst Events anhängt und das Repository die im selben `save()` mit-persistiert, ist nichts weiter zu tun.
- **Sanity-Check:** im `SqlSessionRepository.save` muss `_sync_workspace_events` **vor** `flush()` gerufen werden, sonst landen die Events nicht in der gleichen Transaktion wie der eigentliche Track-Change. Im Bauplan oben bereits so vorgesehen.

Optional (nur falls einfach):
- Reader-Methode `SessionService.list_workspace_events(session_id, user_id, only_unconsumed=False) -> list[WorkspaceEvent]` für Debugging. Greift auf `session.workspace_events` zu. Auth-Pfad wie alle anderen Methoden. **Empfehlung: einbauen**, da kostenlos und nützlich zum Verifizieren.

### 4. Presentation Layer

Bewusst minimal — Schreib-Endpoints brauchen wir nicht, Events entstehen implizit. Lese-Endpoint ist optional aber empfohlen:

- `presentation/schemas.py`:
  ```python
  class WorkspaceEventResponse(Schema):
      id: UUID
      event_type: Literal["track_pinned", "track_unpinned", "track_added", "track_removed"]
      track_id: UUID
      track_title: str
      track_artist: str
      track_spotify_uri: str | None = None
      occurred_at: datetime
      consumed: bool

  class WorkspaceEventListResponse(Schema):
      items: list[WorkspaceEventResponse]
  ```
- `presentation/mapper.py`: `to_workspace_event_response(event: WorkspaceEvent) -> WorkspaceEventResponse`
- `presentation/router.py`: neue Route
  ```python
  @router.get(
      "/{session_id}/workspace-events",
      response_model=WorkspaceEventListResponse,
      operation_id="list_session_workspace_events",
      responses=_auth_errors | _not_found,
  )
  async def list_session_workspace_events(
      session_id: UUID,
      authenticated_user_id: AuthenticatedUserId,
      service: FromDishka[SessionService],
      only_unconsumed: bool = Query(default=False),
  ) -> WorkspaceEventListResponse: ...
  ```

Falls der Debug-Endpoint zu früh ist: weglassen, der Reader auf `SessionService` reicht für Tests aus.

---

## Test-Plan (manuell)

1. Migration rauf — Tabelle existiert, Index existiert.
2. `POST /sessions/{id}/tracks` → Eintrag in `session_workspace_events` mit `event_type=track_added`, `consumed=false`.
3. `POST /sessions/{id}/tracks/{tid}/pin` → neuer Eintrag `track_pinned`.
4. Zweites `pin` auf denselben (schon gepinnten) Track → **kein** neuer Event.
5. `DELETE /sessions/{id}/tracks/{tid}` → neuer Eintrag `track_removed`, `track_title` korrekt gefüllt (Snapshot).
6. Session löschen → workspace_events werden via Cascade mit gelöscht.
7. (Falls Debug-Endpoint gebaut) `GET /sessions/{id}/workspace-events?only_unconsumed=true` → liefert genau die neuen Events.

---

## Was bewusst nicht in diesem Plan ist

- **Konsumieren der Events** (Markieren als `consumed=true`). Das gehört in den Pfad, in dem der Agent die Events liest und in seinen Kontext aufnimmt — Folge-Plan.
- **Prompt-/Kontext-Injection** in den `SessionRunner`. Folge-Plan.
- **Events aus dem Agent-Pfad** (z. B. wenn der Runner selbst Tracks setzt). Aktuell durch Pfadtrennung (Service vs. Runner) automatisch ausgeschlossen — falls sich das ändert, brauchen wir ein `source`-Feld.
- **Frontend-Anzeige der Events.** Falls relevant, separat.

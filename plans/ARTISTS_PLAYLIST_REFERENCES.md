# Artist & Playlist References — Implementation Plan

> Status: **DRAFT — for iteration**. This document is the implementation brief for
> another LLM. It describes a new concept ("references") on the `Session` aggregate,
> the data that gets persisted, and the step-by-step changes across the layers.

## 1. Goal

A `Session` should be able to **reference** Spotify **artists** and **playlists** as
*seed / source material* (e.g. "build me a playlist inspired by these artists and that
playlist"). The UI needs to render these references (name, cover, owner, track count,
genres, …).

**The key constraint:** we store only the *lightweight display metadata* of a referenced
playlist — **NOT** the full track listing of that playlist. A referenced playlist may
contain hundreds of tracks; persisting them would bloat the session, duplicate Spotify
data, and go stale. We persist a compact reference and re-fetch tracks from Spotify only
on demand (e.g. when the agent actually needs them at generation time).

### Non-goals
- Do **not** persist the tracks of a referenced playlist.
- Do **not** turn references into the session's own generated `Playlist` (that already
  exists as `Session.playlist` and *does* hold tracks — see `entities/playlist.py`).
- Do **not** replace `UserMessageAttachment`. See §3 for how the two relate.

## 2. Where this lives

References are **session-scoped**, not message-scoped. They are a curated set of sources
for the whole session, so they belong on the `Session` aggregate as top-level
collections — exactly like `playlist` and `user_curation_events` already are
(`backend/src/backend/features/session/domain/session.py`).

```
Session
├── entries: list[SessionEntry]                  (existing)
├── playlist: Playlist | None                    (existing — owns tracks)
├── user_curation_events: list[...]              (existing)
├── playlist_references: list[PlaylistReference]  ← NEW (no tracks)
└── artist_references: list[ArtistReference]      ← NEW
```

## 3. Relationship to `UserMessageAttachment` (read this carefully)

`UserMessageAttachment` (`entities/messages.py`) **already** carries
`SPOTIFY_PLAYLIST` / `SPOTIFY_ARTIST` kinds with `external_id`, `title`, `subtitle`,
`image_url`, `spotify_id`. That is intentional and stays as-is:

- **`UserMessageAttachment`** = "the user pinned this artist/playlist *to this specific
  message*". It is part of the conversation transcript, immutable, tied to one
  `UserMessage`, and can repeat across messages.
- **`PlaylistReference` / `ArtistReference`** (NEW) = "this artist/playlist is an active
  *source* for the whole session". Deduplicated, session-scoped, can be added/removed
  independently of any message, and carries richer display metadata (genres, followers,
  total_tracks).

**Suggested flow:** when a `UserMessage` with a Spotify attachment is added, the
application service also adds a matching reference onto the session (deduplicated). The
two are kept deliberately separate so the transcript stays faithful while the reference
panel stays a clean, mutable set. (Open question — see §9.)

## 4. Domain model (NEW) — two explicit entities

The fields a Spotify playlist and a Spotify artist expose are **disjoint** (verified
against this repo's own Spotify layer — see the box below). Two separate entities are
therefore clearer than one entity with a `kind` discriminator and a pile of
mutually-exclusive nullable fields.

New file: `backend/src/backend/features/session/domain/entities/reference.py`

```python
from datetime import datetime
from uuid import UUID

from backend.shared.ddd import Entity


class PlaylistReference(Entity):
    """A Spotify playlist referenced as a source for the session.

    Holds display metadata only — NEVER the playlist's tracks.
    """

    def __init__(
        self,
        spotify_playlist_id: str,
        name: str,
        owner: str | None = None,
        cover_url: str | None = None,
        total_tracks: int | None = None,
        id: UUID | None = None,
        created_time: datetime | None = None,
    ) -> None:
        super().__init__(id=id, created_time=created_time)
        self.spotify_playlist_id = spotify_playlist_id
        self.name = name
        self.owner = owner
        self.cover_url = cover_url
        self.total_tracks = total_tracks


class ArtistReference(Entity):
    """A Spotify artist referenced as a source for the session."""

    def __init__(
        self,
        spotify_artist_id: str,
        name: str,
        image_url: str | None = None,
        genres: tuple[str, ...] = (),
        followers: int | None = None,
        popularity: int | None = None,
        id: UUID | None = None,
        created_time: datetime | None = None,
    ) -> None:
        super().__init__(id=id, created_time=created_time)
        self.spotify_artist_id = spotify_artist_id
        self.name = name
        self.image_url = image_url
        self.genres = tuple(genres)
        self.followers = followers
        self.popularity = popularity
```

Export both names from `entities/__init__.py` (add to imports and `__all__`).

> ### ✅ Spotify field verification (do not skip)
> The fields above map 1:1 onto what this repo already pulls from the Spotify Web API.
> Source of truth in this codebase:
> `backend/src/backend/features/spotify/application/ports.py` (the `SpotifyPlaylist` /
> `SpotifyArtist` DTOs) and `infrastructure/spotify_service.py` (`_to_spotify_playlist`
> at ~L369, `_to_spotify_artist` at ~L397).
>
> | Field          | Playlist | Artist | Spotify source                              |
> |----------------|:--------:|:------:|---------------------------------------------|
> | `id`           |    ✓     |   ✓    | object `id`                                 |
> | `name`         |    ✓     |   ✓    | object `name`                               |
> | image          |    ✓     |   ✓    | `images[0].url` (`cover_url` / `image_url`) |
> | `owner`        |    ✓     |   —    | `playlist.owner.display_name`               |
> | `total_tracks` |    ✓     |   —    | `playlist.tracks.total`                     |
> | `genres`       |    —     |   ✓    | `artist.genres` (list[str])                 |
> | `followers`    |    —     |   ✓    | `artist.followers.total`                    |
> | `popularity`   |    —     |   ✓    | `artist.popularity` (0–100)                 |
>
> Playlists have **no** `genres`/`popularity`, and the simplified playlist object this
> repo consumes does **not** carry `followers` — so we deliberately omit those from
> `PlaylistReference`. Artists have **no** `owner`/`total_tracks`. This disjointness is
> exactly why two classes are the right call.

## 5. Aggregate changes — `session.py`

Add two collections, mirroring the `user_curation_events` pattern.

1. **Constructor**: add
   `playlist_references: list[PlaylistReference] | None = None` and
   `artist_references: list[ArtistReference] | None = None`, stored as
   `self._playlist_references = playlist_references or []` /
   `self._artist_references = artist_references or []`.
2. **Properties**:
   ```python
   @property
   def playlist_references(self) -> tuple[PlaylistReference, ...]:
       return tuple(self._playlist_references)

   @property
   def artist_references(self) -> tuple[ArtistReference, ...]:
       return tuple(self._artist_references)
   ```
3. **Mutators** — dedup on the Spotify id; if it already exists, refresh the mutable
   display fields in place and return the existing instance, else append:
   ```python
   def add_playlist_reference(self, *, spotify_playlist_id, name, owner=None,
                              cover_url=None, total_tracks=None) -> PlaylistReference: ...
   def add_artist_reference(self, *, spotify_artist_id, name, image_url=None,
                            genres=(), followers=None, popularity=None) -> ArtistReference: ...
   def remove_playlist_reference(self, reference_id: UUID) -> None: ...
   def remove_artist_reference(self, reference_id: UUID) -> None: ...
   ```
   - `remove_*` raise new `PlaylistReferenceNotFoundError` / `ArtistReferenceNotFoundError`
     (add to `domain/exceptions.py`) when absent — consistent with `remove_track`.

> No new business rules beyond dedup. References do not interact with pinning, curation
> events, or tool-call/follow-up pending state.

## 6. Persisted data — two tables

Two explicit tables, one per entity (no nullable cross-kind columns). Mirrors how the
codebase already keeps a dedicated model per concept.

### `session_playlist_references`

| Column                 | Type                 | Notes                                    |
|------------------------|----------------------|------------------------------------------|
| `id`                   | UUID (PK)            | from `DatabaseEntity`                    |
| `session_id`           | UUID FK → sessions   |                                          |
| `position`             | int                  | preserve insertion order                 |
| `spotify_playlist_id`  | str (max_length=64)  | matches `SessionPlaylistModel` length    |
| `name`                 | str                  | display name                             |
| `owner`                | str \| None          | playlist owner display name              |
| `cover_url`            | str \| None          | cover image                              |
| `total_tracks`         | int \| None          | count for display — NOT the tracks       |
| `created_at`           | datetime             | from `DatabaseEntity`                    |

Unique: `(session_id, spotify_playlist_id)`. Index: `(session_id, position)`.

### `session_artist_references`

| Column               | Type                 | Notes                                      |
|----------------------|----------------------|--------------------------------------------|
| `id`                 | UUID (PK)            | from `DatabaseEntity`                      |
| `session_id`         | UUID FK → sessions   |                                            |
| `position`           | int                  | preserve insertion order                   |
| `spotify_artist_id`  | str (max_length=64)  |                                            |
| `name`               | str                  | display name                               |
| `image_url`          | str \| None          | artist image                               |
| `genres`             | JSON (list[str])     | `Column(JSON, nullable=False)`, default [] |
| `followers`          | int \| None          | artist followers                           |
| `popularity`         | int \| None          | artist popularity (0–100)                  |
| `created_at`         | datetime             | from `DatabaseEntity`                      |

Unique: `(session_id, spotify_artist_id)`. Index: `(session_id, position)`.

ORM models in `backend/src/backend/infrastructure/database/orm.py` (mirror
`SessionUserCurationEventModel`), each with
`session: SessionModel = Relationship(back_populates=...)`. Add two relationships on
`SessionModel`:
```python
playlist_references: list["SessionPlaylistReferenceModel"] = Relationship(
    back_populates="session",
    sa_relationship_kwargs={"cascade": "all, delete-orphan"},
)
artist_references: list["SessionArtistReferenceModel"] = Relationship(
    back_populates="session",
    sa_relationship_kwargs={"cascade": "all, delete-orphan"},
)
```

### Explicitly NOT persisted
- Referenced playlist tracks. `total_tracks` is a count for display; the actual tracks
  are re-fetched from Spotify on demand and never written to any reference table.

### Migration
- Add an Alembic migration creating both tables + indexes + unique constraints. Check how
  existing migrations are generated in this repo (autogenerate, then review).

## 7. Repository changes — `infrastructure/repository.py`

Mirror the `_sync_user_curation_events` / `_to_domain_user_curation_event` pair, once per
table.

1. **Imports**: the two entities + the two ORM models.
2. **`save`** and **`_to_orm`**: call `_sync_playlist_references(...)` and
   `_sync_artist_references(...)` alongside `_sync_user_curation_events`.
3. **`_sync_*_references`**: build rows keyed by existing `id`, set `position` by
   enumeration, assign `orm.playlist_references` / `orm.artist_references`.
4. **`_detail_query`**: add `selectinload(SessionModel.playlist_references)` and
   `selectinload(SessionModel.artist_references)`.
5. **`_to_domain`**: sort each by `position`, map via `_to_domain_playlist_reference` /
   `_to_domain_artist_reference`, pass both lists into the `Session(...)` constructor.
6. **`_to_domain_artist_reference`**: `genres=tuple(row.genres or ())`.
7. Decide whether references count toward `_resolve_last_activity_at` (see §9.3).

## 8. Presentation (display)

`presentation/schemas.py`, `presentation/mapper.py`, and the session detail response.

1. Add two schemas:
   ```python
   class PlaylistReferenceResponse(Schema):
       id: UUID
       spotify_playlist_id: str
       name: str
       owner: str | None = None
       cover_url: str | None = None
       total_tracks: int | None = None

   class ArtistReferenceResponse(Schema):
       id: UUID
       spotify_artist_id: str
       name: str
       image_url: str | None = None
       genres: list[str] = []
       followers: int | None = None
       popularity: int | None = None
   ```
2. Add `playlist_references: list[PlaylistReferenceResponse]` and
   `artist_references: list[ArtistReferenceResponse]` to the session detail response.
3. Map both in `mapper.py`.
4. (Optional, follow-up) REST endpoints to add/remove a reference, and/or an SSE event so
   the reference panel updates live. Out of scope for the first pass unless the UI needs
   mutation without sending a message.

## 9. Open questions (resolve before / during implementation)

1. **Auto-register from attachments?** Should adding a `UserMessage` with a `SPOTIFY_*`
   attachment automatically create a matching reference, or are references created only
   via an explicit "add to sources" action? (Affects the application service.) Note: the
   `UserMessageAttachment` only has `image_url`/`title`/`spotify_id` — it does **not**
   carry `genres`/`followers`/`total_tracks`, so auto-registering may need an extra
   Spotify lookup to fully populate the reference.
2. **Remove semantics**: when a reference is removed, keep the original message
   attachment? (Recommended: yes — transcript is immutable.)
3. **Activity bump**: should adding/removing a reference update `last_activity_at`?
4. **Ordering across kinds**: kept as two independent ordered lists. If the UI needs a
   single merged, chronologically-ordered reference feed, reconsider (would need a shared
   ordering key).

## 10. Suggested implementation order

1. Domain: `reference.py` (`PlaylistReference`, `ArtistReference`), export from
   `entities/__init__.py`.
2. Domain: `Session` constructor, properties, `add_*`/`remove_*`, two exceptions.
3. ORM: two models + two `SessionModel` relationships.
4. Alembic migration (both tables).
5. Repository: two sync methods + two hydrate methods + `_detail_query` + constructor
   wiring.
6. Presentation: two schemas + mapper + detail response.
7. Application: decide §9.1 and wire reference creation.
8. Tests: domain (dedup, remove, not-found per kind), repository round-trip (references
   survive save/load; tracks of referenced playlists are NOT stored).

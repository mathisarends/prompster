# Spotify Web Playback in DeckWorkspaceView

Ziel: In `frontend/src/components/deck/deck-workspace-view.tsx` die Tracks
der aktuellen Playlist über das **Spotify Web Playback SDK** direkt im Browser
abspielen — sicher (Refresh-Token bleibt im Backend), ohne Token-Leak in
LocalStorage, und mit korrekter Behandlung von Premium-/Connect-Edgecases.

---

## 1. Status quo

Was bereits steht und **nicht** angefasst werden muss:

- **Backend Tokens**
  - `GET /api/v1/auth/spotify/token` → `SpotifyAccessTokenResponse`
    (`backend/.../oauth_connections/presentation/spotify_router.py`).
  - Endpoint refreshed bei jedem Call gegen Spotify, rotiert ggf. den Refresh-Token
    (`SpotifyTokenService.get_valid_access_token`), setzt `Cache-Control: no-store`.
  - Refresh-Token Fernet-verschlüsselt persistiert
    (`oauth_connections/infrastructure/fernet_token_cypher.py`).
- **OAuth Flow**
  - Popup-basiert via Sidebar (`navigation-sidebar.tsx`), Postmessage mit
    Origin-Check, `useGetMe()` invalidiert auf Erfolg.
  - Scopes enthalten bereits `streaming`, `user-read-playback-state`,
    `user-modify-playback-state` (`spotify_scopes.py`) — kein Re-Consent nötig.
- **Frontend Client**
  - Orval-generierter Hook `useSpotifyGetAccessToken` +
    `spotifyGetAccessToken()` Funktion.
  - `SpotifyConnectDialog` existiert, wird aber im Workspace noch nicht angezeigt.
  - `user.spotifyConnected` Flag in `UserMeResponse`.

## 2. Lücken

1. **`spotify_uri` wird nicht durchgereicht.** `agent.PlaylistDraftTrack` hat
   das Feld, aber:
   - `backend.session.domain.entities.playlist.PlaylistTrack` kennt es nicht
     (`playlist.py`).
   - `_to_playlist_track` im `session_runner.py:201` kopiert es nicht.
   - `PlaylistTrackResponse` (Pydantic + Orval) enthält es nicht.
   - Repository/DB-Mapping speichert es nicht.
2. **Kein SDK-Loader** im Frontend, keine Spotify-Typen, kein Player-Hook.
3. **`DeckPlaylist` simuliert Playback** mit `setInterval` und Mock-Tracks.
   Muss optional einen echten Controller akzeptieren.
4. **Premium-Pflicht**: Web Playback SDK funktioniert nur mit Spotify Premium.
   Dafür braucht es einen Fallback (Inline-Banner), keinen Crash.

## 3. Architektur — Token-Austausch & Sicherheit

```
Browser (SDK)                       Frontend                Backend
─────────────                       ────────                ───────
new Spotify.Player({
   getOAuthToken: cb => ............ fetchSpotifyToken() ── GET /auth/spotify/token
                                      │                       │ refresh @ Spotify
                                      ◀── access_token ───────┘
   cb(access_token)
}) .................................. (SDK ruft getOAuthToken
                                        bei jedem Bedarf erneut)
player.connect()
```

Kernregeln:

- **Refresh-Token verlässt nie den Server.** Frontend holt nur kurzlebige
  Access-Tokens.
- **Frontend speichert das Access-Token nicht** (kein LocalStorage, kein
  React-Query-Cache). Der Token kommt frisch aus dem Backend in den Callback,
  das SDK hält ihn im Speicher.
- **Refresh ist passiv**: Das SDK selbst ruft `getOAuthToken` immer dann auf,
  wenn sein interner Token expired ist (~60 min) → kein Timer in unserem Code.
- **Direkte Spotify-Web-API Calls** (`/me/player/play` für `play(uris)`) holen
  sich den Token genauso über `fetchSpotifyToken()`.
- **`no-store`** ist auf Backend-Seite schon gesetzt. Wir setzen zusätzlich
  React-Query auf `staleTime: 0`, `gcTime: 0` für diesen Endpoint, falls wir
  ihn überhaupt durch Query laufen lassen (sicherer ist direkter Aufruf).

## 4. Backend-Änderungen

### 4.1 `spotify_uri` propagieren (Pflicht)

Ohne URI kein `play()`. Reihenfolge der Anpassungen:

1. `backend/.../session/domain/entities/playlist.py`
   `PlaylistTrack.__init__` um `spotify_uri: str | None = None` erweitern.
2. Alembic Migration: Spalte `spotify_uri VARCHAR(128) NULL` an der
   Track-Tabelle (Namen via `backend/.../session/infrastructure/repository.py`
   ablesen).
3. Repository-Mapping (`repository.py:458` Read-Pfad und Save-Pfad) ergänzen.
4. `_to_playlist_track` in `session_runner.py:201` kopiert `track.spotify_uri`.
5. `PlaylistTrackResponse` in `session/presentation/schemas.py:84` um
   `spotify_uri: str | None = None`.
6. `to_playlist_track_response` (`session/presentation/mapper.py:135`).
7. SSE-Events in `presentation/sse/events.py` benutzen schon dasselbe Schema —
   automatisch ok.
8. `cd frontend && npm run generate:api` regeneriert das Orval-Modell.

### 4.2 Kein Premium-Check serverseitig

Die SDK feuert `account_error`, wenn ein Free-Account versucht zu starten. Das
genügt; wir bauen einen Frontend-Banner statt eines Backend-Endpoints.

## 5. Frontend-Änderungen

### 5.1 Typen + SDK-Loader

- `cd frontend && npm install -D @types/spotify-web-playback-sdk`.
- Neue Datei `frontend/src/lib/spotify-sdk.ts`:

  ```ts
  let loadPromise: Promise<typeof Spotify> | null = null;

  export const loadSpotifySdk = (): Promise<typeof Spotify> => {
    if (loadPromise) return loadPromise;

    loadPromise = new Promise((resolve, reject) => {
      window.onSpotifyWebPlaybackSDKReady = () => resolve(window.Spotify);
      const script = document.createElement("script");
      script.src = "https://sdk.scdn.co/spotify-player.js";
      script.async = true;
      script.onerror = () => reject(new Error("Spotify SDK failed to load"));
      document.body.appendChild(script);
    });

    return loadPromise;
  };
  ```

- `frontend/src/lib/spotify-token.ts`:

  ```ts
  import { spotifyGetAccessToken } from "@/api/generated/spotify/spotify";

  export const fetchSpotifyAccessToken = async (): Promise<string> => {
    const { accessToken } = await spotifyGetAccessToken();
    return accessToken;
  };
  ```

  Wichtig: **kein** `useQuery` cachen lassen — wir lesen direkt. Falls die
  Token-Antwort einen 409/410 wirft (nicht verbunden / revoked), bubble den
  Fehler hoch; der Hook unten setzt `connectRequired`.

### 5.2 Player-Hook `useSpotifyPlayer`

`frontend/src/hooks/useSpotifyPlayer.ts`:

- Lifecycle:
  1. `loadSpotifySdk()` → `new Spotify.Player({ name, getOAuthToken, volume })`.
  2. Listener registrieren: `ready`, `not_ready`, `player_state_changed`,
     `initialization_error`, `authentication_error`, `account_error`,
     `playback_error`.
  3. `player.connect()`.
  4. Bei Unmount `player.disconnect()` und Promise-Singleton beibehalten.
- State (in `useState` + `useRef`):
  ```ts
  {
    status: "idle" | "loading" | "ready" | "premium-required" | "auth-error" | "error",
    deviceId: string | null,
    isPaused: boolean,
    positionMs: number,
    durationMs: number,
    currentTrackUri: string | null,
  }
  ```
- Position-Tick: nach jedem `player_state_changed` `position` + Wallclock-
  Timestamp speichern und per `requestAnimationFrame`-Loop extrapolieren —
  das Event feuert nicht jede Sekunde.
- API:
  ```ts
  return {
    state,
    playTrack: (uri: string) => Promise<void>, // POST /me/player/play
    resume: () => player.resume(),
    pause: () => player.pause(),
    seek: (ms: number) => player.seek(ms),
    setVolume: (v: number) => player.setVolume(v),
  };
  ```
- `playTrack` ruft die Web-API direkt:
  ```
  PUT https://api.spotify.com/v1/me/player/play?device_id=<id>
  Authorization: Bearer <fresh token via fetchSpotifyAccessToken()>
  Body: { "uris": ["spotify:track:..."] }
  ```
  Bei 401 einmal Token neu holen und retry; bei 403 `premium-required`.

### 5.3 DeckPlaylist entkoppeln

`deck-playlist.tsx` soll **optional** einen Controller akzeptieren:

```ts
type DeckPlaylistController = {
  isPlaying: boolean;
  activeTrackId: string | null;
  positionSeconds: number;
  durationSeconds: number;
  volume: number;
  onPlayTrack: (trackId: string) => void;
  onPause: () => void;
  onResume: () => void;
  onSeek: (seconds: number) => void;
  onVolumeChange: (volume: number) => void;
};
```

Wenn `controller` fehlt → bisheriges Mock-Verhalten (für isolierte Demos).
Wenn vorhanden → kompletter Zustand kommt von außen, `setInterval` entfällt,
`onPlayTrack` ersetzt `activateTrack`.

### 5.4 `DeckWorkspaceView` integrieren

`deck-workspace-view.tsx`:

```ts
const { data: me } = useGetMe();
const player = useSpotifyPlayer();

if (!me?.spotifyConnected) {
  return <SpotifyConnectDialog open onConnect={openSpotifyOAuthPopup} />;
}

if (player.state.status === "premium-required") {
  return <InlineBanner kind="premium" />;
}

const controller = useMemo<DeckPlaylistController>(() => ({
  isPlaying: !player.state.isPaused && !!player.state.currentTrackUri,
  activeTrackId: tracks.find(t => t.spotifyUri === player.state.currentTrackUri)?.id ?? null,
  positionSeconds: player.state.positionMs / 1000,
  durationSeconds: player.state.durationMs / 1000,
  volume: ...,
  onPlayTrack: (trackId) => {
    const t = tracks.find(t => t.id === trackId);
    if (t?.spotifyUri) void player.playTrack(t.spotifyUri);
  },
  onPause: player.pause,
  onResume: player.resume,
  onSeek: (s) => player.seek(s * 1000),
  onVolumeChange: (v) => player.setVolume(v / 100),
}), [player, tracks]);
```

Den OAuth-Popup-Code aus `navigation-sidebar.tsx` in einen kleinen Helper
`useSpotifyOAuthPopup()` extrahieren, damit Sidebar und WorkspaceView ihn
beide nutzen können.

### 5.5 Tracks ohne `spotify_uri` defensiv behandeln

Solange das Agent-Backend lückenhaft Tracks ausspielt (z. B. alte gespeicherte
Sessions), in der UI Tracks ohne URI als "nicht spielbar" markieren
(Play-Button disabled, kleiner Tooltip).

## 6. Reihenfolge / PR-Schnitt

Empfehlung in zwei PRs, damit Review-Größe machbar bleibt:

**PR 1 — Datendurchsatz**
- Backend: `spotify_uri` in Domain, Repo, Mapper, Schema, Migration.
- Agent → Backend Plumbing prüfen.
- Frontend: `npm run generate:api`, `PlaylistTrack` Type um `spotifyUri`
  erweitern, Anzeige unverändert.
- Manuell verifizieren: neue Session, Playlist-Track-Response enthält URI.

**PR 2 — Playback**
- Loader, Token-Helper, `useSpotifyPlayer` Hook.
- `DeckPlaylist` Controller-Prop.
- `DeckWorkspaceView` Integration + Connect/Premium-Gates.
- Manuelle Smoke-Tests (siehe unten).

## 7. Smoke-Test Checklist

1. Spotify im Browser ausgeloggt → Dialog "Spotify verbinden" erscheint im
   Workspace.
2. OAuth-Popup durchgespielt → Workspace zeigt Tracks, Player-Bar aktiv.
3. Doppelklick auf Track → Audio läuft im Browser-Tab, Sound-Bars animieren,
   Cover/Title in der Player-Bar stimmen.
4. Pause/Resume Button reagiert, Slider scrubbed.
5. Lautstärke-Slider regelt hörbar.
6. Tab schließen → im offiziellen Spotify-Client erscheint kein Geister-Device
   (SDK disconnected sauber).
7. Über 60 min im selben Tab spielen → kein Re-Login nötig (`getOAuthToken`
   wurde transparent erneut aufgerufen).
8. Free-Account-User → `premium-required` Banner statt Crash.
9. Track ohne `spotify_uri` → Play-Button disabled, restlicher Player intakt.

## 8. Sicherheits-/Compliance-Notizen

- **Refresh-Token**: bleibt encrypted in der DB, never wire.
- **Access-Token**: Speicher-only im SDK; UI hält ihn nicht in State, keine
  Logs.
- **CSP**: Falls eine Content Security Policy existiert (Vite Plugin oder
  Reverse Proxy), ergänzen:
  - `script-src 'self' https://sdk.scdn.co`
  - `connect-src 'self' https://api.spotify.com wss://*.spotify.com`
- **Origin-Check** im Popup-Flow bleibt unverändert.
- **CORS**: `/auth/spotify/token` läuft mit Credentials → CORS-Settings
  prüfen (sollten schon passen, weil andere Endpoints auch authentifiziert
  laufen).

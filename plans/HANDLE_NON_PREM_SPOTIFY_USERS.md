# Handle Non-Premium / Non-Connected Spotify Users

Ziel: Der Spotify-Web-Player (Bottom-Bar mit Play/Pause/Skip/Seek/Volume) wird **nur** angezeigt, wenn der eingeloggte User
1. ein Spotify-Konto verbunden hat **und**
2. dieses Konto Spotify Premium ist.

In allen anderen Fällen wird die Player-Leiste komplett ausgeblendet. Die Deck-Workspace-View (Playlist + Export) bleibt
voll nutzbar — der User kann weiterhin Tracks suchen, hinzufügen, pinnen, entfernen und nach Spotify exportieren. Nur die
In-Browser-Wiedergabe ist gesperrt.

Sekundäres Ziel: Den heute leicht inkonsistenten State-Salat aufräumen
(`connectRequired`, `premium-required`-Banner, `auth-error`, `enabled`-Flag des Hooks). Es soll genau **eine** Quelle
geben, die entscheidet, ob der Player gezeigt wird.

---

## 1. Status quo (warum überhaupt was tun?)

### Backend
- `User.spotify: SpotifyAccount` mit `connected: bool` und `is_premium: bool` (siehe
  `backend/src/backend/features/user/domain/spotify_account.py`).
- API-Response `UserMeResponse` exponiert beides als `spotify_connected` und `spotify_premium`
  (siehe `backend/src/backend/features/user/presentation/schemas.py:7`,
  `backend/src/backend/features/user/presentation/mapper.py:13`).
- Datenfluss steht — **kein Backend-Change nötig**.

### Frontend
- Generierter Typ `UserMeResponse` enthält `spotifyConnected` **und** `spotifyPremium`
  (`frontend/src/api/generated/model/userMeResponse.ts:9`).
- `deck-workspace-view.tsx` nutzt heute aber **nur** `me?.spotifyConnected`:
  - `useSpotifyPlayer({ enabled: Boolean(me?.spotifyConnected) })` (Zeile 70)
  - `connectRequired = (!isMeLoading && !me?.spotifyConnected) || playerState.status === "auth-error"` (Zeile 174)
- Premium-Fall wird erst *reaktiv* nach einem fehlgeschlagenen Play-Versuch erkannt
  (`account_error` / `403` → `playerState.status === "premium-required"`) und zeigt nur ein
  kleines amber Banner über der Playlist (Zeile 304–309). Der Player rendert trotzdem weiter
  unten und tut so, als könne man abspielen — schlechte UX.

### Konsequenz
Wir haben den Premium-Flag schon in der API, verwenden ihn im Frontend aber nirgends. Das ist der eigentliche Hebel.

---

## 2. Zielzustand (UX)

Drei klare Fälle, abgeleitet aus `me.spotifyConnected` und `me.spotifyPremium`:

| Fall | spotifyConnected | spotifyPremium | UI |
|------|------------------|----------------|----|
| A    | `false`          | (egal)         | `SpotifyConnectDialog` blockierend, **kein** Player |
| B    | `true`           | `false`        | Inline-Hinweis „Premium erforderlich", **kein** Player, Playlist + Export voll nutzbar |
| C    | `true`           | `true`         | Player aktiv, alles wie bisher |

Während `useGetMe` lädt (`isMeLoading`) wird gar nichts entschieden — kein Dialog, kein Player, kein Banner — sonst
flackert die UI.

Zusatzfall D (Edge): `me.spotifyConnected === true && spotifyPremium === true`, aber zur Laufzeit kommt vom Spotify-SDK
trotzdem ein `account_error` (z. B. Premium gekündigt zwischen Login und jetzt). → Fallback: Player wird ausgeblendet,
Inline-Hinweis erscheint, `useGetMe` wird invalidiert.

---

## 3. Implementierungsschritte

### 3.1 Quelle der Wahrheit zentralisieren

In `deck-workspace-view.tsx` einen abgeleiteten `spotifyMode`-Wert einführen, der die ganze UI-Logik trägt:

```ts
type SpotifyMode = "loading" | "disconnected" | "non-premium" | "ready";

const spotifyMode: SpotifyMode = useMemo(() => {
  if (isMeLoading || !me) return "loading";
  if (!me.spotifyConnected) return "disconnected";
  if (!me.spotifyPremium) return "non-premium";
  return "ready";
}, [isMeLoading, me]);
```

Diese eine Variable ersetzt:
- die direkte Nutzung von `me?.spotifyConnected` als `enabled`
- die Berechnung von `connectRequired`
- die Bedingung für das Premium-Banner

### 3.2 Hook nur im `ready`-Fall aktivieren

```ts
const player = useSpotifyPlayer({ enabled: spotifyMode === "ready" });
```

`useSpotifyPlayer` reagiert bereits auf `enabled` (Cleanup-Branch in
`frontend/src/hooks/useSpotifyPlayer.ts:135-144`). Dadurch werden für Fälle A und B keine SDK-Skripte geladen, keine
Token-Requests abgefeuert, keine Devices abgefragt. Spart Traffic, vermeidet 409/403-Noise im Network-Tab.

### 3.3 Controller bedingt durchreichen

`DeckPlaylist` rendert die Player-Leiste (`DeckPlayer`) anhand der Anwesenheit von `controller`. Wir wollen den Player
explizit verstecken, wenn `spotifyMode !== "ready"`:

```ts
const controller = spotifyMode === "ready" ? buildController(player, ...) : undefined;
```

`DeckPlaylist` selber muss minimal angepasst werden:
- Heute wird `<DeckPlayer ... />` **immer** gerendert (Zeile 351).
- Neu: `<DeckPlayer />` nur rendern, wenn `controller` gesetzt ist
  (oder ein neues optionales Prop `showPlayer: boolean`, default `true`, das wir aus der Workspace-View steuern).

Empfehlung: **`controller`-Anwesenheit als Signal nutzen** (kein zusätzliches Prop). Begründung: `usePlaybackState`
liefert in `DeckPlaylist` heute schon einen Local-Fallback, wenn kein Controller da ist — für unseren Fall wollen wir
diesen Fallback aber **nicht** anzeigen, sondern komplett verstecken. → entweder
- `usePlaybackState` so anpassen, dass es ohne Controller `null` zurückgibt und `DeckPlayer` dann nicht rendert, **oder**
- in `DeckPlaylist` einen expliziten Check `if (!controller) return null` vor dem `<DeckPlayer />`-Block.

Die zweite Variante ist kleiner und sicherer (kein Risiko für andere Konsumenten von `usePlaybackState`).

### 3.4 Connect-Dialog nur bei `disconnected`

```ts
<SpotifyConnectDialog
  open={spotifyMode === "disconnected"}
  onConnect={openSpotifyOAuthPopup}
  isConnecting={isSpotifyOAuthLoading}
/>
```

Den OR-Zweig `|| playerState.status === "auth-error"` ersetzen wir bewusst — siehe 3.6 zum Drift-Recovery-Pfad.

### 3.5 Inline-Hinweis im `non-premium`-Fall

Das heutige amber Banner über der Playlist (Zeile 304–309) wird umfunktioniert. Statt auf `playerState.status` zu
schauen, hängt es jetzt an `spotifyMode === "non-premium"`. Inhalt bleibt im Kern gleich, aber etwas freundlicher und
mit Hinweis, dass Playlist + Export trotzdem funktionieren:

> **Spotify Premium erforderlich für In-Browser-Wiedergabe.** Du kannst die Playlist weiterhin kuratieren und nach
> Spotify exportieren — die Wiedergabe findet dann in deiner Spotify-App statt.

Optional: Link/Button „Premium-Konto verbinden" → öffnet erneut den OAuth-Popup, falls der User nach Upgrade neu
verbinden will. Erstmal weglassen; reine Info-Pille reicht.

### 3.6 Drift-Recovery (Edge-Case D)

Wenn `spotifyMode === "ready"` ist, der Hook aber doch `premium-required` oder `auth-error` meldet (Token abgelaufen,
Premium gekündigt, Account-Wechsel):

```ts
useEffect(() => {
  if (spotifyMode !== "ready") return;
  if (playerState.status === "premium-required" || playerState.status === "auth-error") {
    queryClient.invalidateQueries({ queryKey: getGetMeQueryKey() });
  }
}, [spotifyMode, playerState.status, queryClient]);
```

Beim nächsten `useGetMe`-Refetch fällt der User dann sauber in Fall A oder B zurück, Player verschwindet, Hinweis
erscheint. Kein extra State im Component.

### 3.7 Cleanup nach dem Refactor

Folgende heute existierende Stellen werden überflüssig und können raus:
- `connectRequired`-Variable.
- Das `playerState.status === "premium-required"`-Banner-JSX **in seiner alten Form** (wird durch das neue
  `non-premium`-Banner ersetzt).
- Die Statusprüfung `previous.status === "premium-required" ? previous.status : "ready"` in `onPlayerStateChanged`
  (`useSpotifyPlayer.ts:213-216`) kann bleiben — sie schützt nur den Hook-internen State; der Workspace ignoriert sie
  künftig ohnehin.

---

## 4. Tests

### 4.1 Frontend (Vitest / Testing Library)

Neue Tests in `frontend/src/components/deck/__tests__/deck-workspace-view.test.tsx` (falls noch nicht vorhanden,
sonst dort ergänzen):

- **A**: `useGetMe` liefert `{ spotifyConnected: false }` → `SpotifyConnectDialog` ist im Markup, `DeckPlayer`-Bar
  nicht im Markup, `useSpotifyPlayer` wird mit `enabled: false` aufgerufen (Mock).
- **B**: `{ spotifyConnected: true, spotifyPremium: false }` → kein Dialog, kein Player, aber das Premium-Hinweis-Banner
  ist sichtbar; Playlist + Export sind interaktiv.
- **C**: `{ spotifyConnected: true, spotifyPremium: true }` → Player wird gerendert, kein Banner, kein Dialog.
- **Loading**: `isLoading: true` → weder Dialog noch Player noch Banner (kein Flackern).
- **Drift**: Start in C, Hook meldet `premium-required` → erwartet, dass `queryClient.invalidateQueries` für die
  Me-Query aufgerufen wird.

### 4.2 Backend

Kein Code-Change → keine neuen Tests. Bestehende Tests in
`backend/tests/backend/features/user/application/test_user_service.py` und
`backend/tests/backend/features/user/presentation/test_user_presentation_router.py` decken `spotify_premium` bereits ab;
einmal querlesen, ob beide Werte `(true, false)` Kombinationen abgedeckt sind, sonst minimal ergänzen.

---

## 5. Reihenfolge der PRs

Ein einzelner PR reicht. Diff ist klein, Änderungen sind kohärent, und die Tests sollen zusammen mit der Logik gemerged
werden. Aufteilen würde nur Reviewer-Churn erzeugen.

Branch-Vorschlag: `feat/hide-player-for-non-premium`.

---

## 6. Was bewusst **nicht** Teil dieses Plans ist

- **Upgrade-CTA / Spotify-Premium-Link**: Wir verlinken nicht aktiv auf `spotify.com/premium`. Falls später erwünscht,
  einfach im Inline-Hinweis aus 3.5 ergänzen.
- **Backend-Reaktion auf Premium-Verlust** (z. B. Server-seitiges Sperren des Exports): Export funktioniert auch ohne
  Premium über die Spotify-Web-API, also kein Handlungsbedarf.
- **Polling auf Premium-Status-Änderungen**: Die `useGetMe`-Invalidierung aus 3.6 deckt den realistischen Pfad ab
  (User probiert zu spielen, scheitert, UI lädt Me neu). Kein Background-Poll nötig.
- **Migration / DB-Änderungen**: `is_premium` existiert seit `0013_add_oauth_connection_is_premium.py` bereits.

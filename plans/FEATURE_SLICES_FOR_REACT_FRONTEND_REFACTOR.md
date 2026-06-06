# Feature-Sliced Refactor – Prompster Frontend

> Ziel: Das `frontend/src` von einer **technischen** Ordnung (`components/`, `hooks/`,
> `lib/`) auf eine **feature-orientierte** Ordnung umstellen. Pro Seite soll wieder
> klar sein, welches Feature dort gerendert wird und wer wofür verantwortlich ist.
> Geteilte Bausteine (`shared`) werden sauber von feature-spezifischen getrennt.

---

## 1. Leitprinzipien

1. **Co-location nach Feature, nicht nach Technik.** Alles, was zu einem Feature
   gehört (Components, Hooks, State, API-Calls, Typen, Utils), liegt im selben
   Feature-Ordner – nicht über `components/`, `hooks/`, `lib/` verstreut.
2. **Zwei Sichtbarkeits-Ebenen:**
   - `src/shared/*` – generisch, feature-agnostisch, von überall importierbar.
   - `src/features/<feature>/*` – nur im Kontext genau dieses Features sinnvoll.
3. **Feature-Public-API über `index.ts`.** Andere Features / Pages importieren
   **nur** aus dem Barrel (`@/features/chat`), nie aus internen Pfaden
   (`@/features/chat/components/...`).
4. **Komposition passiert auf Page-/Route-Ebene.** Wenn zwei Features zusammen
   auftreten (Chat + Deck im selben Split-View), verdrahtet die *Page* sie – die
   Features kennen einander möglichst nicht.
5. **Abhängigkeitsrichtung ist azyklisch:**
   `shared → (nichts)`, `features → shared`, `pages → features + shared`,
   `app/routes → pages`. Niemals `feature → feature` quer, niemals `feature → page`.

---

## 2. Ist-Zustand & Probleme

### 2.1 Heutige Struktur (verkürzt)
```
src/
  api/            generated/ (orval) + http-client + *-stream.ts
  auth/           ← schon ein sauberer Feature-Slice
  components/
    chat/         ~25 Dateien + attachments/ follow-up-questions/
                  tool-call-sequence/ user-curation/
    deck/         ~12 Dateien + export/ search-panel/
    sidebar/      Navigation + Session-History + Session-Dialoge
    shared/       keyboard-shortcut-hint, ui/chip
    ui/           shadcn-Primitives (button, dialog, ...)
  features/       ← LEER (Zielordner existiert schon)
  hooks/          17 Hooks flach gemischt (feature-spezifisch + generisch)
  layouts/        app-layout
  lib/            utils + spotify-sdk + spotify-token + playlist-track
  pages/          chat-page(.tsx/.hook.ts/.state.ts), home-page, landing-page
  routes/         app-routes
```

### 2.2 Konkrete Probleme
- **`components/` vermischt Ebenen.** `ui/` + `shared/` (geteilt) liegen neben
  `chat/`, `deck/`, `sidebar/` (feature-spezifisch). Man sieht einem Import nicht
  an, ob er „shared“ oder „feature“ ist.
- **`hooks/` und `lib/` sind globale Sammelkörbe.** Feature-Hooks wie
  `useSpotifyPlayer`, `useDeckPlayerController`, `usePlaybackState`,
  `useRealtimeTranscription`, `useSessionStarActions` stehen neben echten
  Shared-Hooks (`useLocalStorage`, `useViewport`, `useDebouncedValue`). Gleiches
  bei `lib/spotify-*`.
- **Quer-Abhängigkeiten zwischen Features** (heute „zufällig“ möglich, weil alles
  unter `components/` liegt):
  | Leak | heute | Problem |
  |------|-------|---------|
  | `chat-page.state.ts` → `components/chat/tool-call-sequence` | State importiert Component-Typen | State/Logik hängt an UI |
  | `deck-workspace-view` → `components/chat/chat-workspace-panel` | deck → chat | Deck kennt Chat-Shell |
  | `navigation-sidebar` → `components/chat/chat-search-dialog` | sidebar → chat | Such-Dialog falsch verortet |
- **Große, überladene Dateien** (Top-Verursacher):
  | Datei | Zeilen |
  |-------|-------:|
  | `components/chat/chat-input-box.tsx` | 789 |
  | `pages/chat-page.state.ts` | 787 |
  | `components/deck/deck-playlist.tsx` | 555 |
  | `hooks/useSpotifyPlayer.ts` | 516 |
  | `components/chat/attachments/attachment-popover.tsx` | 399 |
  | `components/chat/onboarding-panel.tsx` | 370 |
  | `components/deck/deck-player.tsx` | 353 |
  | `hooks/useRealtimeTranscription.ts` | 351 |
- **`pages/chat-page.tsx` macht zu viel:** Routing-State, Media-Query-Logik,
  User-Curation-Player-Bridge (Refs + State), Layout-Persistenz und Komposition in
  einer Datei (238 Zeilen, viel davon Glue-Logik, die in Hooks gehört).

---

## 3. Ziel-Architektur

```
src/
  app/                      # App-Shell: Provider, Router, Layout (bisher routes/ + layouts/ + App.tsx)
    app.tsx
    app-routes.tsx
    app-layout.tsx
    providers.tsx           # QueryClient, AuthProvider, Tooltip, Sonner ...

  pages/                    # NUR Komposition: welche Features rendert diese Route?
    landing-page.tsx
    home-page.tsx
    chat-page.tsx           # dünn: holt useChatSession aus features/chat, ordnet Panels an

  features/
    auth/                   # (Umzug aus src/auth/)
      components/  hooks/  index.ts
    chat/
      components/           # session-pane, messages, input-box, onboarding, tool-call-sequence ...
      hooks/                # use-chat-session, use-chat-input-attachments, use-realtime-transcription, use-smooth-streaming-text
      state/                # chat-reducer (heute chat-page.state.ts) + types
      api/                  # session-stream.ts
      index.ts              # Public API
    deck/
      components/           # playlist, player, timeline, export/, search-panel/, user-curation playback
      hooks/                # use-deck-player-controller, use-playback-state
      index.ts
    spotify/                # Integrations-/Capability-Feature (von deck konsumiert)
      lib/                  # spotify-sdk, spotify-token, playlist-track
      hooks/                # use-spotify-player, use-spotify-oauth-popup
      components/           # spotify-connect-dialog
      index.ts
    sessions/               # Session-Historie + Navigation (bisher components/sidebar/)
      components/           # navigation-sidebar*, session-item, session-dialogs, session-search-dialog
      hooks/                # use-session-star-actions
      lib/                  # session-history-utils
      index.ts

  shared/
    ui/                     # shadcn-Primitives (aus components/ui/)
    components/             # keyboard-shortcut-hint, chip, markdown-renderer, workspace-panel-shell
    hooks/                  # useLocalStorage, useViewport, useDebouncedValue, useKeyboardShortcut,
                            # usePlatform, useWheel, useDocumentTitle, useStickyScroll,
                            # useBufferedControlledValue, useOptimisticRemoval
    lib/                    # utils (cn), ...
    api/                    # http-client.ts

  api/
    generated/              # orval-Output – bleibt unangetastet (generiert)
```

> **Hinweis zu `api/generated`:** wird von orval erzeugt (`orval.config.ts`) und
> bleibt zentral. Feature-`api/`-Ordner kapseln nur *handgeschriebene* Aufrufe
> (Streams, Mappings) um den generierten Client herum.

---

## 4. Anatomie eines Feature-Slices

Jeder Feature-Ordner folgt demselben Schema (nur anlegen, was gebraucht wird):

```
features/<feature>/
  components/      # nur in diesem Feature verwendete React-Components
  hooks/           # nur in diesem Feature verwendete Hooks
  api/             # Datenzugriff: Streams, Mapper, Query-Wrapper
  state/           # Reducer / Stores / Maschinen
  lib/             # reine Helfer/Utils ohne React
  types.ts         # geteilte Feature-Typen
  index.ts         # PUBLIC API – einziger erlaubter Außen-Import
```

**Regel für `index.ts`:** exportiert nur, was Pages/andere Slices wirklich
brauchen (z. B. `ChatPage`-Bausteine, `useChatSession`). Interne Helfer bleiben
ungeexportiert → verhindert ungewollte Kopplung.

---

## 5. Abhängigkeits-Regeln (durchsetzbar machen)

Erlaubte Importrichtungen:
- `shared/*` → nur `shared/*` (idealerweise gar nichts feature-spezifisches)
- `features/*` → `shared/*`, `api/generated`
- `pages/*` → `features/*`, `shared/*`
- `app/*` → `pages/*`, `features/*`, `shared/*`

Verboten: `feature A → feature B` (außer dem Capability-Feature `spotify`, das
bewusst von `deck` konsumiert wird – siehe §7), und `feature → page`.

**Durchsetzung (Phase am Ende):** `eslint-plugin-boundaries` oder
`import/no-restricted-paths`, plus tsconfig-Pfad-Aliase:
```jsonc
"paths": {
  "@/app/*":      ["src/app/*"],
  "@/pages/*":    ["src/pages/*"],
  "@/features/*": ["src/features/*"],
  "@/shared/*":   ["src/shared/*"],
  "@/api/*":      ["src/api/*"]
}
```

---

## 6. Datei-Mapping (Ist → Ziel)

### → `shared/`
| heute | ziel |
|-------|------|
| `components/ui/*` | `shared/ui/*` |
| `components/shared/keyboard-shortcut-hint.tsx` | `shared/components/` |
| `components/shared/ui/chip.tsx` | `shared/ui/chip.tsx` |
| `components/chat/markdown-renderer.tsx` | `shared/components/` (generisch) |
| `components/chat/chat-workspace-panel.tsx` | `shared/components/workspace-panel-shell.tsx` (löst deck→chat Leak) |
| `lib/utils.ts` | `shared/lib/utils.ts` |
| `api/http-client.ts` | `shared/api/http-client.ts` |
| `hooks/useLocalStorage, useViewport, useDebouncedValue, useKeyboardShortcut, usePlatform, useWheel, useDocumentTitle, useStickyScroll, useBufferedControlledValue, useOptimisticRemoval` | `shared/hooks/` |

### → `features/chat/`
| heute | ziel |
|-------|------|
| `pages/chat-page.hook.ts` | `features/chat/hooks/use-chat-session.ts` |
| `pages/chat-page.state.ts` | `features/chat/state/chat-reducer.ts` (+ `types.ts`) |
| `api/session-stream.ts` | `features/chat/api/session-stream.ts` |
| `components/chat/*` (Messages, Input-Box, Onboarding, Thinking, Send, Header, Session-Pane, attachments/, follow-up-questions/, tool-call-sequence/, user-curation/, transcription-button) | `features/chat/components/...` |
| `hooks/useRealtimeTranscription, useSmoothStreamingText` | `features/chat/hooks/` |
| `components/chat/use-chat-input-attachments.ts` | `features/chat/hooks/` |
| `components/chat/chat-search-dialog.tsx` | **→ `features/sessions/`** (es sucht über Sessions, nicht Chat-intern) |

> **Tool-call-Typen entkoppeln:** Die in `chat-page.state.ts` aus
> `tool-call-sequence` importierten Typen (`ToolCallItem`, `ToolCallStatus`) nach
> `features/chat/types.ts` ziehen; die Component importiert sie von dort. Damit
> hängt der Reducer nicht mehr an einer Component.

### → `features/deck/`
| heute | ziel |
|-------|------|
| `components/deck/{deck-playlist, deck-player, deck-timeline, deck-playlist-track-item, deck-workspace-view, player-slider, search-bar}` | `features/deck/components/` |
| `components/deck/export/*`, `components/deck/search-panel/*` | `features/deck/components/export|search-panel/` |
| `hooks/useDeckPlayerController, usePlaybackState` | `features/deck/hooks/` |
| `components/chat/user-curation/*` | `features/deck/components/user-curation/` (Curation = Deck-Tracks; in Chat-Messages nur *gerendert*, Playback via Props-Bridge) |

### → `features/spotify/` (Capability-Feature)
| heute | ziel |
|-------|------|
| `lib/spotify-sdk.ts, spotify-token.ts, playlist-track.ts` | `features/spotify/lib/` |
| `hooks/useSpotifyPlayer, useSpotifyOAuthPopup` | `features/spotify/hooks/` |
| `components/deck/spotify-connect-dialog.tsx` | `features/spotify/components/` |
| `api/transcription-stream.ts` | `features/chat/api/` *(Transkription gehört zur Chat-Eingabe)* |

### → `features/sessions/`
| heute | ziel |
|-------|------|
| `components/sidebar/*` | `features/sessions/components/` |
| `components/sidebar/session-history-utils.ts` | `features/sessions/lib/` |
| `hooks/useSessionStarActions` | `features/sessions/hooks/` |
| `components/chat/chat-search-dialog.tsx` | `features/sessions/components/session-search-dialog.tsx` |

### → `features/auth/`
| heute | ziel |
|-------|------|
| `auth/*` | `features/auth/` (1:1 Umzug, schon sauber) |

### → `app/`
| heute | ziel |
|-------|------|
| `routes/app-routes.tsx` | `app/app-routes.tsx` |
| `layouts/app-layout.tsx` | `app/app-layout.tsx` |
| `App.tsx` | `app/app.tsx` (+ neues `providers.tsx`) |

---

## 7. Cross-Cutting-Entscheidungen (lösen die Leaks aus §2.2)

1. **`deck → chat` (ChatWorkspacePanel):** Panel ist eine generische Scroll-/
   Layout-Shell. → nach `shared/components/workspace-panel-shell.tsx`. Danach
   importiert Deck nicht mehr aus Chat.
2. **`sidebar → chat` (ChatSearchDialog):** Der Dialog sucht über *Sessions*. →
   gehört zu `features/sessions`. Danach kein Sidebar→Chat-Import.
3. **`state → component` (Tool-Call-Typen):** Typen ins Feature
   (`features/chat/types.ts`) hochziehen; Reducer und Component importieren von
   dort. Reducer hängt nicht mehr an UI.
4. **`spotify` als bewusstes Capability-Feature:** `deck` darf `@/features/spotify`
   (Public API) konsumieren. Das ist die *einzige* erlaubte Feature→Feature-Kante
   und wird in der ESLint-Boundaries-Config explizit erlaubt.
5. **User-Curation-Bridge aus `chat-page.tsx` extrahieren:** Die Ref/State-Bridge
   (`updateUserCurationTrackPlayer`, `toggleUserCurationEventTrackPlayback`) wird
   ein Hook `useUserCurationPlaybackBridge` in `features/deck/hooks/`. Die Page
   bleibt reine Komposition.

---

## 8. Decompose-Targets (begleitend, nicht blockierend)

Beim Umzug die größten Dateien gleich aufteilen (jeweils nach Verantwortung):
- **`chat-input-box.tsx` (789):** Eingabe-State / Attachments-Anbindung /
  Transkription / Render aufsplitten; Logik in `hooks/`, Subviews in `components/`.
- **`chat-page.state.ts` (787):** `chat-reducer.ts` (Maschine) vs. `types.ts` vs.
  `event-handlers/` (pro Event-Typ) trennen.
- **`deck-playlist.tsx` (555):** Liste vs. Item-Interaktion vs. Drag/Reorder.
- **`useSpotifyPlayer.ts` (516):** SDK-Lifecycle vs. Playback-State vs.
  Transport-Controls.
- **`attachment-popover.tsx` (399)** und **`onboarding-panel.tsx` (370):** Such-/
  Auswahl-Logik in Hooks, Präsentation in kleinere Components.

> Regel of thumb: Ziel < ~200 Zeilen pro Datei; Hooks raus aus Components.

---

## 9. Inkrementeller Migrationsplan (jede Phase ist lauffähig)

> Technik: pro Schritt `git mv`, dann Imports anpassen, `tsc --noEmit` + Tests
> grün, committen. Aliase früh einführen, damit Pfade stabil bleiben.

- **Phase 0 – Gerüst.** `src/shared/`, `src/features/`, `src/app/` anlegen.
  tsconfig-/vite-Aliase (`@/shared`, `@/features`, `@/app`, `@/pages`) ergänzen.
  Kein Code-Umzug. *(klein, risikolos)*
- **Phase 1 – `shared` herauslösen.** `ui/`, generische Components, generische
  Hooks, `lib/utils`, `http-client` umziehen. Reine Imports-Updates, keine Logik.
- **Phase 2 – `auth` umziehen.** `src/auth → features/auth` (1:1, einfachstes
  Feature als Pilot für das Slice-Schema + Barrel).
- **Phase 3 – `spotify`-Capability-Feature.** `lib/spotify-*`, `useSpotifyPlayer`,
  `useSpotifyOAuthPopup`, `spotify-connect-dialog` bündeln + Public API. Erlaubte
  Boundary `deck → spotify` definieren.
- **Phase 4 – `sessions`-Feature.** Sidebar + Session-Dialoge + Such-Dialog +
  `useSessionStarActions` + History-Utils. Löst `sidebar→chat`-Leak.
- **Phase 5 – `deck`-Feature.** Deck-Components + Deck-Hooks + User-Curation.
  Vorher `chat-workspace-panel → shared` ziehen (löst `deck→chat`-Leak).
- **Phase 6 – `chat`-Feature.** `chat-page.hook.ts`, `chat-page.state.ts`,
  `session-stream`, alle Chat-Components. Tool-Call-Typen entkoppeln. Page-Bridge
  als Hook extrahieren.
- **Phase 7 – Pages & `app` aufräumen.** `chat-page.tsx` auf reine Komposition
  reduzieren; `routes/` + `layouts/` + `App.tsx` → `app/` mit `providers.tsx`.
- **Phase 8 – Enforcement.** ESLint-Boundaries-Regeln aktivieren, verbleibende
  Verstöße fixen. Begleitend Decompose-Targets (§8) angehen.

Reihenfolge-Logik: erst „Blätter“ (shared, auth, spotify), dann Features, die nur
auf shared/spotify zeigen (sessions, deck), zuletzt das verflochtenste (chat) und
die Komposition (pages/app). So bleibt nach jeder Phase alles importierbar.

---

## 10. Offene Entscheidungen (vor Phase 5/6 klären)

1. **`sessions` eigenes Feature oder Teil von `chat`?** Vorschlag: eigenes Feature
   (Sidebar/Historie ist von einer einzelnen Chat-Session unabhängig).
2. **User-Curation Ownership:** `deck` (Vorschlag, da Track-zentriert) vs. `chat`
   (wird in Messages gerendert). Bridge via Props bleibt so oder so.
3. **`spotify` als Feature vs. `shared/integrations/spotify`?** Vorschlag: Feature,
   weil es eigene UI (Connect-Dialog) + Lifecycle hat, nicht nur Utils.
4. **Barrel-Granularität:** ein `index.ts` pro Feature (Vorschlag) vs. zusätzliche
   Sub-Barrels (`components/index.ts`). Sub-Barrels nur bei Bedarf.

---

## 11. Definition of Done

- [ ] `src/components/`, `src/hooks/`, `src/lib/` (global) existieren nicht mehr;
      Inhalte liegen in `shared/` oder einem Feature.
- [ ] Jedes Feature hat ein `index.ts`; Außen-Imports laufen nur darüber.
- [ ] Keine `feature → feature`-Kante außer `deck → spotify`.
- [ ] `chat-page.tsx` enthält keine Player-Bridge-/Media-Query-Logik mehr (in Hooks).
- [ ] Keine Datei > ~250 Zeilen ohne bewussten Grund.
- [ ] ESLint-Boundaries grün, `tsc --noEmit` grün, Tests grün.

# Prompster frontend

Lit 3, TypeScript, Vite und TanStack Lit Query. Die Gestaltung und der
Codegenerierungsablauf basieren auf `maximus-trading/frontend`: dunkle Flächen,
Geist-Schriften, gemeinsame Design-Tokens und ein Chat mit Deck-Arbeitsbereich.
Musikkarten und ein heller grüner Akzent passen das Design an Prompster an.

## Starten

Node.js 24 und npm verwenden:

```sh
npm ci
npm run dev
```

Vite leitet `/api` inklusive WebSockets an `http://127.0.0.1:8000` weiter.
Das vorhandene Backend muss laufen; die Anwendung enthält keine Demo-Anmeldung
oder simulierte KI-Antworten. `.env.example` dokumentiert getrennte API- und
OAuth-Origins. Im Development öffnet OAuth den Backend-Port 8000, passend zu
den vorhandenen Callback-Seiten. Cookies, erlaubte Origins und OAuth-Redirects
müssen auf dieselbe Host-Schreibweise (z. B. `127.0.0.1`) abgestimmt sein.

Produktionshosting benötigt einen SPA-Fallback für `/new`, `/chat/:id`, `/decks`
und `/settings` sowie einen Proxy für HTTP und WebSockets unter `/api`.

## Aufbau

```text
src/
  app/                     # Session-Gate, Routen und Layout
  api/
    request.ts             # Fetch, Cookies, einmaliger Session-Refresh, PDF, Fehler
    query-client.ts        # gemeinsamer Query-Cache
    generated/<tag>/       # api.ts, models.ts, queries.ts, mutations.ts, index.ts
    session-rpc/           # unveränderter, von rpckit erzeugter WebSocket-Client
  features/
    auth/                  # Login-Seite und OAuth-ReactiveController
    chat/                  # Chat-Seite, ChatController, reiner Stream-Reducer
      components/          # Nachrichtenliste, Rückfragen, Anhänge
      api/                 # typisierte OpenRPC-Streams
    deck/                  # Deck-Panel, DeckController, Musik-Karten, Exporte
    sessions/              # Sammlung und Query-/Mutation-Verwaltung
    settings/              # Konto und Spotify-Verbindung
    spotify/               # Suche, PlaybackController, SDK-Service
  shared/
    ui/                    # wiederverwendbare UI: Sidebar, Chat, Breadcrumb, Logo
    styles/                # native Controls, Workspace- und Seitenstile
    api/                   # Integration des generierten RPC-Clients
  style.css                # gemeinsame Farben, Typografie und Radien
```

Komponenten erhalten Daten als Properties und melden Absichten über typisierte,
bubbelnde `CustomEvent`s. Shared UI kennt keine Backend-Services. Reactive
Controller besitzen asynchrone Abläufe, Abbruchsignale und Lifecycle-Aufräumen.
Der bestehende fachliche Chat-Reducer bleibt unabhängig von Lit. Imports nutzen
`@app`, `@api`, `@features`, `@shared` und `@chat`; der Alias `@/` bleibt für
übernommene RPC- und Reducer-Module verfügbar.

## HTTP- und RPC-Generierung

Die echte API-Spec liegt in `openapi.json`. Sie wird direkt aus der vorhandenen
FastAPI-Anwendung exportiert. Orval erzeugt pro OpenAPI-Tag unabhängige Module.
Der AST-basierte Nachlauf aus der Vorlage normalisiert Funktionssignaturen,
URL-Parameter und Query-/Mutation-Optionen. `system` wird ausgelassen.
OAuth-GETs gelten als Aktionen; im UI starten sie per Popup-Navigation.

```sh
npm run api:export          # Backend-Umgebung über uv erforderlich
npm run api:generate        # Spec -> Fetch-Funktionen + TanStack-Optionen
npm run api:check-backend   # Backend -> Spec ohne Drift
npm run api:check           # Spec -> generierter Client ohne Drift
npm run generate:rpc       # vorhandener OpenRPC-Vertrag und Client
npm run check:rpc
```

`generate:api` bleibt als Alias erhalten. `download:openapi` kann alternativ
von einer laufenden API exportieren; `OPENAPI_URL` überschreibt deren Adresse.
`OPENAPI_SPEC_PATH` überschreibt den Orval-Eingang. Generierte Dateien werden
nicht von Hand bearbeitet. Ein zusätzlicher Prüfprozess erkennt fehlgeschlagene
Orval-Post-Hooks auch dann, wenn Orval selbst Exit-Code 0 liefert.

`apiFetch` liefert den typisierten Body direkt, `undefined` für leere Antworten
und einen `Blob` für PDFs. Fehler werfen `ApiError` mit HTTP-Status und
Problem-Details. Gleichzeitige 401-Antworten teilen sich genau einen Refresh;
AbortSignals, Multipart-Uploads und wiederholte Query-Parameter bleiben erhalten.
Fachliche Cache-Invalidierung gehört in die Feature-Controller.

## Funktionsumfang und Prüfungen

Google-/Spotify-Anmeldung, Session-Liste, Favoriten, Umbenennen und Löschen,
Modellauswahl, Live-Chat mit Recherche-Schritten, Onboarding-Rückfragen,
Bild- und Spotify-Referenzen, Songsuche, Entfernen und Wiederherstellen von
Tracks, Spotify-Premium-Wiedergabe, PDF-Vorschau/-Download und Spotify-Export
mit Retry-Anzeige sind an die bestehenden Schnittstellen angeschlossen.

```sh
npm run build
npm run lint
npm test
npm run test:e2e
```

Die Browser-Tests verwenden kontrollierte HTTP- und WebSocket-Antworten und
prüfen Desktop sowie Mobil. Unter Windows nutzen sie installiertes Chrome;
andernfalls einmal `npx playwright install chromium` ausführen. Echte OAuth-
Provider, Spotify-Premium-Wiedergabe und Modellanbieter benötigen verbundene
Konten und einen gesonderten Live-Test. CI prüft Formatierung, Typen, Build,
HTTP-Codegenerierung, Unit- und Browser-Tests; Backend-CI prüft zusätzlich die
Spec und den bestehenden RPC-Client.

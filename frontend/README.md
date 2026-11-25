# Prompster frontend

Lit 3, TypeScript, Vite und TanStack Lit Query. Die Gestaltung und der
Codegenerierungsablauf basieren auf `maximus-trading/frontend`: dunkle Flächen,
Geist-Schriften, gemeinsame Design-Tokens und ein Chat mit Deck-Arbeitsbereich.
Musikkarten und ein heller grüner Akzent passen das Design an Prompster an.

## Starten

Node.js 24 und die in `package.json` angegebene pnpm-Version verwenden.
Die Befehle laufen im Verzeichnis `frontend`.

```sh
pnpm install --frozen-lockfile
pnpm run dev
```

Vite leitet `/api` an `http://127.0.0.1:8000` weiter.
Das vorhandene Backend muss laufen; die Anwendung enthält keine Demo-Anmeldung
oder simulierte KI-Antworten. `.env.example` dokumentiert getrennte API- und
OAuth-Origins. Im Development öffnet OAuth den Backend-Port 8000, passend zu
den vorhandenen Callback-Seiten. Cookies, erlaubte Origins und OAuth-Redirects
müssen auf dieselbe Host-Schreibweise (z. B. `127.0.0.1`) abgestimmt sein.

Produktionshosting benötigt einen SPA-Fallback für `/new`, `/chat/:id`, `/decks`
und `/settings` sowie einen Proxy unter `/api`, der Server-Sent Events nicht puffert.

## Aufbau

```text
src/
  app/                     # Session-Gate, Routen und Layout
  api/
    request.ts             # Fetch-Konfiguration und einmaliger Session-Refresh
    query-client.ts        # gemeinsamer Query-Cache
    generated/<tag>/       # HTTP-Client, Modelle, Query Keys und TanStack-Optionen
    session-streams/       # unveränderter, von fastapi-canon erzeugter SSE-Client
  features/
    auth/                  # Login-Seite und OAuth-ReactiveController
    chat/                  # Chat-Seite, ChatController, reiner Stream-Reducer
      components/          # Nachrichtenliste, Rückfragen, Anhänge
      api/                 # typisierte SSE-Streams
    deck/                  # Deck-Panel, DeckController, Musik-Karten, Exporte
    sessions/              # Sammlung und Query-/Mutation-Verwaltung
    settings/              # Sprache, Konto und Spotify-Verbindung
    spotify/               # Suche, PlaybackController, SDK-Service
  shared/
    i18n/                  # Locale-Auswahl, Intl-Formatierung und generierte Übersetzungen
    ui/                    # wiederverwendbare UI: Sidebar, Chat, Breadcrumb, Logo
    styles/                # native Controls, Workspace- und Seitenstile
    api/                   # Integration des generierten SSE-Clients
  style.css                # gemeinsame Farben, Typografie und Radien
```

Komponenten erhalten Daten als Properties und melden Absichten über typisierte,
bubbelnde `CustomEvent`s. Shared UI kennt keine Backend-Services. Reactive
Controller besitzen asynchrone Abläufe, Abbruchsignale und Lifecycle-Aufräumen.
Der bestehende fachliche Chat-Reducer bleibt unabhängig von Lit. Imports nutzen
`@app`, `@api`, `@features`, `@shared` und `@chat`; der Alias `@/` bleibt für
übernommene Stream- und Reducer-Module verfügbar.

## HTTP- und Stream-Generierung

Die API-Spec in `openapi.json` kommt direkt aus FastAPI. `lit-canon-api` erzeugt
pro OpenAPI-Tag einen typisierten Client, Query Keys und TanStack-Optionen.
`lit-canon-api.config.ts` lässt `system` aus und behandelt OAuth-GETs als Aktionen.
Im UI starten diese Aktionen per Popup-Navigation.

`lit-canon-api` und `lit-canon-fetch` werden beim Installieren aus demselben
gepinnten [GitHub-Commit](https://github.com/mathisarends/lit-canon/commit/02e362ad9684005270f907b97ec4260bf2d9b924)
gebaut. Für ein Update beide Pins in `package.json` und die zugehörigen
Build-Freigaben in `pnpm-workspace.yaml` anpassen, dann `pnpm install` und
`pnpm run api:generate` ausführen. Das Lockfile und den generierten Client
gemeinsam committen.

```sh
pnpm run api:export          # Backend-Umgebung über uv erforderlich
pnpm run api:generate        # Spec -> Fetch-Funktionen + TanStack-Optionen
pnpm run api:generate --watch # Client bei Änderungen der Spec aktualisieren
pnpm run api:check-backend   # Backend -> Spec ohne Drift
pnpm run api:check           # Spec -> generierter Client ohne Drift
pnpm run generate:streams   # Backend -> Stream-Vertrag + SSE-Client
pnpm run check:streams
```

`generate:api` bleibt als Alias erhalten. `download:openapi` kann alternativ
von einer laufenden API exportieren; `OPENAPI_URL` überschreibt deren Adresse.
`OPENAPI_SPEC_PATH` überschreibt den Eingang des Generators. Generierte Dateien
werden ausschließlich über den Generator aktualisiert.

`lit-canon-fetch` verarbeitet JSON, Multipart-Uploads und PDFs und liefert
`ApiError` mit HTTP-Status und Problem-Details. Prompsters Fetch-Middleware
bündelt gleichzeitige 401-Antworten in einem Cookie-Refresh und berücksichtigt
abgebrochene Requests. Die Feature-Controller nutzen generierte Query Keys für
die Cache-Invalidierung.

## Funktionsumfang und Prüfungen

Google-/Spotify-Anmeldung, Session-Liste, Favoriten, Umbenennen und Löschen,
Modellauswahl, Live-Chat mit Recherche-Schritten, Onboarding-Rückfragen,
Bildanhänge, Songsuche, Entfernen und Wiederherstellen von
Tracks, Spotify-Premium-Wiedergabe, PDF-Vorschau/-Download und Spotify-Export
mit Retry-Anzeige sind an die bestehenden Schnittstellen angeschlossen.

```sh
pnpm run build
pnpm run lint
pnpm test
pnpm run test:e2e
pnpm run i18n:check
```

Die Browser-Tests verwenden kontrollierte HTTP- und SSE-Antworten und
prüfen Desktop sowie Mobil. Unter Windows nutzen sie installiertes Chrome;
andernfalls einmal `pnpm exec playwright install chromium` ausführen. Echte OAuth-
Provider, Spotify-Premium-Wiedergabe und Modellanbieter benötigen verbundene
Konten und einen gesonderten Live-Test. CI prüft Formatierung, Typen, Build,
HTTP-Codegenerierung, vollständige Übersetzungen, Unit- und Browser-Tests; Backend-CI prüft zusätzlich die
Spec und den generierten SSE-Client.

## Mehrsprachigkeit

Deutsch und Englisch verwenden [Lit Localize im Runtime-Modus](https://lit.dev/docs/localization/runtime-mode/).
Die Sprachauswahl befindet sich ausschließlich in den Einstellungen und
wechselt die Sprache ohne Neuladen. Beim Besuch der Einstellungen bleiben das
Studio und seine Komponenten verbunden; offene Tabs, Entwürfe und Deckdaten bleiben
erhalten. Die Reihenfolge beim Start ist: gespeicherte Auswahl unter
`prompster.locale`, erste unterstützte Browsersprache (auch `en-GB`/`de-AT`),
sonst Deutsch. Die Auswahl gilt für diesen Browser. Ohne Local Storage bleibt
das Umschalten möglich; ein fehlgeschlagenes Sprachmodul blockiert den Start nicht.
Englisch wird als separates Modul geladen. `html.lang`, Seitentitel, Beschreibung,
Zahlen, Datumsangaben, Singular/Plural und zugängliche Beschriftungen wechseln mit.

Deutsche Quelltexte stehen in `msg(...)` direkt bei der jeweiligen Ansicht.
`@localized()` aktualisiert die Lit-Komponente bei einem Sprachwechsel. Dynamische
Texte verwenden `msg(str\`… ${value} …\`)`, damit Übersetzungen Platzhalter
umstellen können. Ganze Sätze übersetzen; Textteile nicht zusammenkleben.
`msg()`beim Rendern oder in einer Funktion aufrufen, nicht einmalig auf Modulebene.
Mehrzahlformen und wiederverwendbare dynamische Texte liegen in`src/shared/i18n/messages.ts`. Nutzertexte, Songtitel, Künstler und Antworten oder
Statusbeschreibungen des Backends bleiben Inhalt und werden nicht umgeschrieben.
Die UI-Sprache ändert weder den API-Vertrag noch die Sprache bestehender Chats
oder des serverseitigen PDF-Generators.

```sh
pnpm run i18n:extract   # msg-Aufrufe -> locales/en.xlf; bestehende Übersetzungen bleiben erhalten
# Alle neuen <target>-Texte in locales/en.xlf übersetzen; <x>-Platzhalter beibehalten.
pnpm run i18n:build     # XLIFF -> src/shared/i18n/generated/en.ts + locale-codes.ts
pnpm run i18n:check     # Vollständigkeit, Platzhalter und Abweichungen der generierten Dateien
```

XLIFF und generierte Module werden gemeinsam eingecheckt. Generierte Dateien
nicht manuell bearbeiten. CI lehnt fehlende, leere, veraltete oder ungültige
Übersetzungen ab. Für eine weitere Sprache `targetLocales` in `lit-localize.json`
ergänzen, die Sprachauswahl und `speechLocale()` erweitern, das neue XLIFF
übersetzen und bei Bedarf weitere `Intl.PluralRules`-Kategorien ergänzen.

Browser-Tests prüfen DE/EN auf Desktop und Mobil, gespeicherte Auswahl,
Browserpräferenzen, Datumsformatierung, erhaltene Entwürfe und Tabs, Diktiersprache,
gesperrten Speicher sowie fehlgeschlagene Sprachdownloads.

## Review-Aufnahmen

Die [Review-Galerie](../docs/reviews/lit-frontend/README.md) enthält Desktop- und
Mobil-Screenshots, MP4-Videos und animierte Vorschauen. `pnpm run review:capture`
erstellt die Aufnahmen gegen den laufenden Vite-Server mit den kontrollierten
Browser-Testdaten neu. Voraussetzungen und Video-Konvertierung stehen in der
Galerie.

## Workspace, Karten und Diktieren

Der Deck-Arbeitsbereich reicht über die gesamte Fensterhöhe. Playlist, Karten
und Export sind per Tabs erreichbar (auch mit Pfeiltasten, Pos1 und Ende);
die Ansicht lässt sich vergrößern und wieder neben den Chat stellen. Auf Mobil
ersetzt das geöffnete Deck den Chat bis zum Schließen.

Die Icon-Aktionen zeigen beim Hover ihren Namen und vorhandene Tastenkürzel.
Dieselben Kürzel sind über `aria-keyshortcuts` für assistive Technik verfügbar.
`src/shared/shortcuts.ts` hält Anzeige und Tastaturbehandlung zusammen; modale
Dialoge, wiederholte Tastenereignisse, AltGr und laufende IME-Eingaben werden berücksichtigt.

| Aktion                           | Tastenkürzel                                                |
| -------------------------------- | ----------------------------------------------------------- |
| Seitenleiste umschalten          | Strg/⌘ + B                                                  |
| Neues Deck                       | Alt + N                                                     |
| Deck öffnen/schließen            | Alt + Umschalt + D                                          |
| Deck vergrößern/geteilte Ansicht | Alt + Umschalt + F                                          |
| Einstellungen                    | Strg/⌘ + ,                                                  |
| Nachricht senden                 | Enter im Textfeld; Umschalt + Enter für einen Zeilenumbruch |
| Diktat verwerfen                 | Esc im Composer                                             |

Die quadratischen Karten folgen dem „Zeitkapsel“-Design aus `deck.typ`: Das
Albumcover steckt im Medium seiner Zeit (LP bis 1981, Kassette bis 1991, CD bis
2007, danach Stream), und die Kartenfarben stammen aus dem Cover selbst. Die
Regeln dafür stehen in `card-design.ts` und müssen zu `cover_palette.py` und
`deck.typ` im Backend passen. Die verdeckte Seite ist dieselbe Karte vor der
Auflösung: Der lokal erzeugte Spotify-QR-Code sitzt an der Stelle des Covers,
Künstler, Titel und Jahr sind Platzhalter. Die druckfertige Datei mit
Schnittmarken kommt weiterhin vom PDF-Generator.

Das Mikrofon übernimmt den Ablauf aus der Referenz: Browser-Spracherkennung
(`SpeechRecognition` / `webkitSpeechRecognition`), Live-Transkription in der
ausgewählten Sprache (`de-DE` oder `en-US`),
anschließend Übernehmen oder Verwerfen. In Chrome ist dies die
[Web-Speech-Anbindung](https://developer.chrome.com/blog/voice-driven-web-apps-introduction-to-the-web-speech-api/),
keine separate Google-Cloud-API. Erkanntes wird erst nach Bestätigung an den
Entwurf angehängt und nie automatisch gesendet. Abbrechen, Session-Wechsel, der
Besuch der Einstellungen und Unmount beenden die Aufnahme und verwerfen verspätete Events. HTTPS bzw.
localhost, Mikrofonfreigabe und ein unterstützender Browser sind erforderlich;
die Erkennung kann den Dienst des Browsers über das Netzwerk verwenden.
Eine laufende Aufnahme behält ihre Sprache bis zum Ende; die nächste Aufnahme
verwendet die aktuelle Auswahl.

Tests und Review-Videos verwenden einen simulierten Spracherkennungsdienst,
damit sie ohne echten Mikrofonzugriff reproduzierbar sind. Ein Live-Test der
Spracherkennung mit dem eigenen Mikrofon bleibt erforderlich.

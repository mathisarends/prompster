# Integration von `pyrpckit` als WebSocket-first Presentation Layer

Status: Architektur- und Integrationsspezifikation, noch keine Implementierung.

Grundlage dieser Spezifikation ist `pyrpckit` ab Version `0.3.0` und der Stand
des Repositories [`mathisarends/pyrpckit`](https://github.com/mathisarends/pyrpckit)
vom 10.09.2026 (`98fd152e4ead8e5287da41245cd66989212f7950`). Bei der
Implementierung sollte die Version zunächst exakt gepinnt werden, weil das
Protokoll und insbesondere die generierten Runtime-Dateien noch jung sind.

## Kurzfassung der Entscheidung

Für eine geöffnete Session wird genau ein langlebiger, ressourcengebundener
JSON-RPC-2.0-WebSocket verwendet:

```text
wss://<host>/api/v1/sessions/{session_id}/rpc
```

Solange der Benutzer den Session-Channel geöffnet hat, bleibt dieser Socket
verbunden. Über ihn laufen:

- Conversation-Kommandos wie Nachricht senden, Onboarding abschließen und Run
  stoppen;
- interaktive Session-Kommandos wie Track hinzufügen/entfernen und
  Curation-Event wiederherstellen;
- alle typisierten, serverseitig initiierten Session- und Agent-Events;
- Synchronisation nach Verbindungsaufbau oder Reconnect.

`pyrpckit` bleibt dabei ausschließlich im Presentation Layer. Domain,
Application Services, `SessionRunner` und Agent kennen weder JSON-RPC noch
WebSockets. Der WebSocket-Adapter übersetzt JSON-RPC-Kommandos in Application
Commands und Application Events zurück in `session.event`-Notifications.

Nicht alles sollte zwanghaft über den Socket gehen. Binärdaten, Downloads und
OAuth-Flows bleiben HTTP:

- Image-Upload und signierte Attachment-URLs;
- PDF-Download;
- Spotify-/Google-OAuth Redirects und Callbacks;
- Health-, OpenAPI- und OpenRPC-Dokumente;
- Session-Liste und Session-Erzeugung können zunächst REST bleiben, da sie
  außerhalb eines geöffneten Channels stattfinden.

Damit wird die Architektur **WebSocket-first innerhalb einer Session**, nicht
WebSocket-only für die gesamte Anwendung.

## Warum der aktuelle SSE-Schnitt ersetzt werden sollte

Aktuell sind `send_message` und `complete_onboarding` HTTP-POSTs, deren
Lebensdauer direkt an einen SSE-Response gekoppelt ist:

```text
POST /messages
  -> SessionConversationService.send_message() als AsyncIterator
  -> SessionRunner.run()
  -> SSE-Mapping
  -> fetch()-Response-Stream im Browser
```

Das führt zu mehreren parallelen API-Modellen:

- OpenAPI/Orval generiert normale Request/Response-Clients;
- Streaming wird in `frontend/src/features/chat/api/session-stream.ts`
  zusätzlich von Hand implementiert;
- Event-Typen werden über Schema-Hilfsrouten künstlich in OpenAPI sichtbar
  gemacht;
- `remove_playlist_track` und `restore_user_curation_event` laufen als separate
  REST-Aufrufe und erfordern danach einen vollständigen Refetch;
- der Transport-Request, der Agent-Run und der UI-Streamingzustand sind unnötig
  eng gekoppelt.

`pyrpckit` löst den Contract-Teil davon gut: Methoden und serverseitige
Notifications stehen gemeinsam in OpenRPC, und daraus entsteht ein typisierter
TypeScript-Client. Es liefert bewusst keinen FastAPI-WebSocket-Adapter, keinen
Event-Broker und keinen Run-Scheduler. Diese drei Teile bleiben
Prompster-Verantwortung.

## Zielbild

```text
React / useChatSession
        |
        | generierter PrompsterRpcClient
        | JSON-RPC requests + notifications
        v
FastAPI WebSocket /sessions/{session_id}/rpc
        |
        +-- ConnectionContext(user_id, session_id, connection_id)
        +-- RpcServer (pro Connection gebunden)
        +-- ein Reader + ein serialisierter Writer
        |
        v
SessionRpcMethods                  SessionEventPublisher
        |                                  ^
        | Application Commands             | Application Events
        v                                  |
Session Services / RunCoordinator / Session Actor
        |
        +-- Repository/UoW pro Kommando oder Event-Batch
        +-- AgentSessionRunner
        +-- Agent + DeckStore
```

Wichtige Grenzen:

1. `pyrpckit` definiert und dispatcht das Wire-Protokoll.
2. Der FastAPI-Adapter besitzt Connection-Lifecycle, Authentifizierung,
   Backpressure und konkurrierende Requests.
3. Application Services validieren Autorisierung und Use Cases.
4. Ein `SessionRunCoordinator` besitzt die Lebensdauer laufender Agent-Runs.
5. Ein Event-Publisher verteilt Events an alle aktuell verbundenen Clients der
   Session und später optional über Redis/Postgres Pub/Sub an weitere Instanzen.

## Vorgeschlagenes RPC-Protokoll

### Namensraum und Notification

Ein Router genügt zunächst:

```python
session_rpc = RpcRouter(
    namespace="session",
    tags=("session",),
    server="session-channel",
)
```

Alle fachlichen Events werden über genau eine Notification transportiert:

```python
@session_rpc.notification("event")
def session_event() -> SessionRpcEvent:
    """Canonical session state and agent-run updates."""
```

Auf dem Wire lautet sie `session.event`. `SessionRpcEvent` ist eine
discriminated union aus den bereits vorhandenen Event-Payloads. Die bestehenden
`type`-Literale wie `message.assistant_chunk`, `playlist.track_removed` und
`session.suspended_for_input` passen direkt zum `pyrpckit`-Modell.

Alle RPC-Modelle sollten von `pyrpckit.RpcModel` erben. Dadurch gelten am
Protokollrand einheitlich:

- Python in `snake_case`, JSON/TypeScript in `camelCase`;
- unbekannte Felder werden abgelehnt;
- Request-, Result- und Notification-Modelle stehen direkt im OpenRPC-Contract.

Die bisherigen `Schema`-Modelle können intern weiterverwendet werden. Für den
RPC-Rand sollte es aber eigene Modelle bzw. ein bewusstes gemeinsames Basismodell
geben; eine zufällige Mischung aus permissivem `Schema` und strengem `RpcModel`
sollte vermieden werden.

### Gemeinsame Metadaten jedes Events

Die derzeitigen SSE-Events sollten für den langlebigen Kanal ergänzt werden:

```python
class SessionEventMeta(RpcModel):
    event_id: UUID
    session_id: UUID
    session_revision: int
    occurred_at: datetime
    run_id: UUID | None = None
```

Jedes `SessionRpcEvent` enthält diese Felder direkt oder als `meta`. Empfohlen
wird ein flaches Modell, weil der Frontend-Reducer dann leichter damit arbeitet.

- `event_id` macht die Verarbeitung idempotent.
- `session_revision` erkennt Lücken und veraltete Antworten.
- `run_id` ordnet Chunks, Tool Calls, Fehler und Abschluss dem richtigen Run zu.
- `session_id` schützt vor versehentlichem Cross-Channel-Dispatch.

Für einen ersten Spike kann `session_revision` noch nur monoton pro Prozess
sein. Für produktionssicheres Replay muss die Revision zusammen mit der
Session-Änderung persistiert werden.

### Methoden

| Wire-Methode | Parameter | Resultat | Zweck |
| --- | --- | --- | --- |
| `session.sync` | `afterRevision?` | `SessionSyncResult` | Snapshot und aktiven Run nach Connect/Reconnect laden |
| `session.message.send` | Content, Attachments, `modelId?`, `commandId` | `RunAccepted` | User-Nachricht persistieren und Run starten |
| `session.message.stop` | `runId`, `commandId` | `RunStopResult` | exakt den aktuellen Run stoppen |
| `session.onboarding.answer.submit` | Question-ID, Antwort(en), `commandId` | `CommandApplied` | Onboarding-Antwort speichern |
| `session.onboarding.complete` | `modelId?`, `commandId` | `RunAccepted` | Phase wechseln und Agent-Run starten |
| `session.playlist.track.add` | Trackdaten, `commandId` | `CommandApplied` | manuellen Track hinzufügen |
| `session.playlist.track.addSpotify` | Spotify-URI, `commandId` | `CommandApplied` | Spotify-Track auflösen und hinzufügen |
| `session.playlist.track.remove` | `trackId`, `commandId` | `CommandApplied` | Track entfernen und Curation-Event erzeugen |
| `session.curationEvent.restore` | `eventId`, `commandId` | `CommandApplied` | Curation-Änderung rückgängig machen |
| `session.run.get` | keine oder `runId?` | `RunStatus` | Run-Zustand nach unklarem Timeout abfragen |

`commandId` ist eine vom Client erzeugte UUID. Sie ist für mutierende Methoden
verpflichtend und wird serverseitig pro Session dedupliziert. Das verhindert,
dass ein Reconnect oder Timeout dieselbe Nachricht bzw. Track-Mutation doppelt
ausführt.

Beispielmodelle:

```python
class SendMessageParams(RpcModel):
    command_id: UUID
    content: str
    model_id: str | None = None
    attachments: list[SessionMessageAttachmentRpc] = Field(default_factory=list)
    image_attachments: list[ImageAttachmentReferenceRpc] = Field(
        default_factory=list,
    )


class RunAccepted(RpcModel):
    command_id: UUID
    run_id: UUID
    session_revision: int
    status: Literal["accepted"] = "accepted"


class CommandApplied(RpcModel):
    command_id: UUID
    session_revision: int
    status: Literal["applied", "duplicate"]


class SessionSyncResult(RpcModel):
    session: SessionResponse
    session_revision: int
    active_run: RunStatus | None = None
```

Die Methodenklasse ist **connection-bound**. `session_id` und `user_id` sind
nicht Teil jedes RPC-Requests, sondern werden nach Handshake in den Handler
gebunden:

```python
class SessionRpcMethods:
    def __init__(
        self,
        *,
        context: SessionConnectionContext,
        commands: SessionCommandGateway,
    ) -> None:
        self._context = context
        self._commands = commands

    @session_rpc.method("sync", errors=(SessionNotFound, SessionAccessDenied,))
    async def sync(self, params: SyncSessionParams) -> SessionSyncResult:
        return await self._commands.sync(
            session_id=self._context.session_id,
            user_id=self._context.user_id,
            after_revision=params.after_revision,
        )

    @session_rpc.method(
        "message.send",
        errors=(
            SessionNotFound,
            SessionAccessDenied,
            MessageRateLimitExceeded,
            SessionRunAlreadyActive,
        ),
    )
    async def send_message(self, params: SendMessageParams) -> RunAccepted:
        return await self._commands.send_message(
            session_id=self._context.session_id,
            user_id=self._context.user_id,
            params=params,
        )

    @session_rpc.method(
        "playlist.track.remove",
        errors=(SessionNotFound, SessionAccessDenied, PlaylistTrackNotFound),
    )
    async def remove_track(self, params: RemoveTrackParams) -> CommandApplied:
        return await self._commands.remove_track(
            session_id=self._context.session_id,
            user_id=self._context.user_id,
            track_id=params.track_id,
            command_id=params.command_id,
        )
```

Die Resultate sind Acknowledgements. Die kanonische UI-Änderung kommt als
`session.event`-Notification. So erhalten auch ein zweiter Tab oder ein späterer
kollaborativer Client dieselbe Änderung. Der Reducer muss Events anhand von
`event_id`/`session_revision` idempotent anwenden.

### Run- und Lifecycle-Events

Die bestehende Union bleibt fachlich weitgehend erhalten. Ergänzt werden sollte:

```text
run.accepted
run.started
run.completed
run.cancelled
run.failed
```

`done` ist im SSE-Modell ein Ende des HTTP-Streams. Auf einem dauerhaften Socket
hat es diese Bedeutung nicht mehr und sollte durch `run.completed` ersetzt
werden. Ebenso ist `error` zu unspezifisch:

- Fehler eines JSON-RPC-Kommandos werden als JSON-RPC Error Response geliefert;
- Fehler eines bereits akzeptierten Hintergrund-Runs werden als
  `run.failed`-Notification mit `runId` geliefert;
- Transportfehler schließen bzw. reconnecten den Socket.

Die vorhandenen Events `SessionSnapshot`, `SessionAssistantMessage*`,
`SessionToolCall*`, `SessionPlaylist*`, `SessionTitleGenerated`,
`SessionContextCompacted`, `SessionOnboardingQuestionAsked` und
`SessionSuspendedForInput` werden weiterhin im Application Layer erzeugt und
nur noch durch einen RPC-Mapper serialisiert.

## FastAPI-WebSocket-Adapter

### Route und Authentifizierung

Vorgeschlagene Route:

```python
@router.websocket("/{session_id}/rpc")
async def session_rpc_socket(
    websocket: WebSocket,
    session_id: UUID,
    authenticated_user_id: AuthenticatedUserId,
    ...,
) -> None:
    ...
```

Die bestehende Auth-Dependency unterstützt bereits `HTTPConnection` und
`WebSocket`; Cookie-basierte Access Tokens können daher beim Upgrade validiert
werden. Zusätzlich muss **vor oder unmittelbar nach `accept()`** geprüft werden,
dass der Benutzer Zugriff auf die konkrete Session hat. Bei Fehlschlag wird mit
WebSocket-Code `1008` geschlossen, ohne Domain-Details preiszugeben.

Empfohlenes Subprotocol:

```text
prompster.rpc.v1
```

Origin-Allowlist, maximale Message-Größe und Auth-Cookie-Einstellungen müssen
für WebSockets explizit getestet werden. CORS-Middleware allein ersetzt keine
Origin-Prüfung beim WebSocket-Handshake.

### Bindung von `pyrpckit`

Der `RpcApp` und sein OpenRPC-Contract sind statisch auf App-Ebene. Der
`RpcServer` wird dagegen pro Connection an einen `SessionRpcMethods`-Handler
gebunden, damit `user_id`, `session_id` und `connection_id` nicht als frei
fälschbare Payloads gesendet werden.

```python
RPC_APP = RpcApp(version=1)
RPC_APP.include_router(session_rpc)

# pro erfolgreichem Handshake
server = RPC_APP.bind(
    SessionRpcMethods(context=context, commands=command_gateway),
    error_mapper=to_rpc_error,
)
```

### Reader, Dispatch und Writer

Ein naiver Loop wie

```python
response = await server.handle(await websocket.receive_json())
await websocket.send_json(...)
```

ist für Prompster nicht ausreichend: Ein lang laufender Handler würde den Reader
blockieren, sodass `message.stop` nicht mehr empfangen werden könnte.

Der Adapter braucht deshalb:

- genau einen Reader-Task;
- Dispatch jedes Requests in einen begrenzten Task;
- genau einen Writer-Task mit bounded `asyncio.Queue`;
- Serialisierung aller Responses und Notifications durch diesen Writer;
- ein Limit für parallele Requests pro Connection;
- sauberes Canceln der **Request-Tasks** beim Disconnect, aber nicht automatisch
  des bereits angenommenen Agent-Runs;
- Logging mit `connection_id`, `session_id`, `request_id`, `method` und `run_id`.

Skizze:

```python
async def dispatch(raw: object) -> None:
    response = await server.handle(raw)
    if response is not None:
        await outbound.put(response.model_dump(mode="json", by_alias=True))

async with asyncio.TaskGroup() as tasks:
    tasks.create_task(write_messages(websocket, outbound))
    async for raw in receive_messages(websocket):
        limiter.acquire_nowait_or_raise()
        tasks.create_task(dispatch_limited(raw, limiter, outbound))
```

Die konkrete Implementierung benötigt zusätzlich ein getrenntes Lifecycle für
Reader/Writer und Dispatch-Tasks, damit ein normaler Disconnect die TaskGroup
nicht als Serverfehler eskalieren lässt.

`pyrpckit.RpcNotification` wird vom Publisher erzeugt und ebenfalls in die
Writer-Queue gelegt:

```python
RpcNotification(method="session.event", params=rpc_event)
```

### Backpressure

Der generierte TypeScript-WebSocket-Transport besitzt aktuell eine begrenzte
Notification Queue (Default 100) und schließt bei Overflow. Auch serverseitig
muss die Queue begrenzt sein.

Für hochfrequente `message.assistant_chunk`-Events gilt:

- kleine Token-Deltas serverseitig für etwa 20–50 ms bündeln;
- maximal eine konfigurierbare Queue-Größe pro Connection;
- keine stillen Drops kanonischer State-Events;
- bei einem dauerhaft langsamen Client Verbindung kontrolliert schließen und
  über Reconnect plus `session.sync` wiederherstellen;
- Metriken für Queue-Auslastung, Drops/Close und Chunk-Latenz erfassen.

## Entkopplung des Agent-Runs vom Transport

Dies ist die wichtigste notwendige Änderung. Heute konsumiert der SSE-Response
direkt den `AsyncIterator` von `SessionConversationService`. Zukünftig muss eine
RPC-Methode schnell ein `RunAccepted` zurückgeben, während der Run unabhängig
weiterläuft.

### Neuer `SessionRunCoordinator`

Vorgeschlagenes Application-Port-Interface:

```python
class SessionRunCoordinator(Protocol):
    async def start_message(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
        command_id: UUID,
        content: str,
        model_id: str | None,
        attachments: list[SessionMessageAttachment],
        image_attachments: list[SessionImageAttachmentReference],
    ) -> RunReceipt: ...

    async def complete_onboarding(...) -> RunReceipt: ...
    async def stop(self, *, session_id: UUID, run_id: UUID) -> RunStopResult: ...
    async def status(self, *, session_id: UUID) -> RunStatus | None: ...
```

Der Coordinator:

1. autorisiert und validiert den Command;
2. dedupliziert `command_id`;
3. erzeugt/persistiert `run_id` und Zustand `accepted`;
4. startet einen Application-scope Background-Task;
5. konsumiert darin den bestehenden `SessionRunner`;
6. persistiert Events/Session-Zustand in kurzen Units of Work;
7. veröffentlicht die Events über den `SessionEventPublisher`;
8. persistiert den terminalen Run-Zustand auch ohne verbundenen Client.

Der derzeitige `ActiveSessionRunStore` ist eine gute Basis, benötigt aber einen
expliziten `run_id`, Status und idealerweise Start-/Endzeit sowie Fehlerklasse.
Der `AgentRuntimeRegistry` bleibt als In-Process-Optimierung für sofortiges Stoppen
bestehen. Die Datenbank bleibt die Wahrheit für Recovery und mehrere Worker.

### Keine langlebige Request-DB-Session

Ein WebSocket darf nicht für seine gesamte Lebensdauer eine Dishka-`REQUEST`-
scoped `AsyncSession` und damit potenziell eine DB-Verbindung halten. RPC-Handler
sollten stattdessen ein Gateway/Factory injiziert bekommen, das pro Kommando bzw.
Event-Batch einen kurzen Request-/Unit-of-Work-Scope öffnet.

Auch Background-Runs dürfen keine Dependency aus dem ursprünglichen
WebSocket-Request-Scope behalten. Der Coordinator muss alle benötigten
Application Services aus einem neuen Scope beziehen.

### Verhalten bei Disconnect

Ein Browser-Disconnect bedeutet nicht automatisch „Run stoppen“:

- Navigation, Laptop-Sleep und Netzwechsel dürfen den Run nicht vernichten;
- der Run schreibt weiter in den persistenten Session-Zustand;
- nach Reconnect liefert `session.sync` den aktuellen Snapshot und `activeRun`;
- neue Events werden wieder live zugestellt;
- explizites Stoppen erfolgt ausschließlich über `session.message.stop`.

Als spätere Policy kann ein orphaned Run nach einem konfigurierbaren Timeout
abgebrochen werden. Das ist eine Produktentscheidung und darf nicht implizit aus
dem Socket-Close folgen.

## Konsistenz von Playlist und aktivem Agent

Der gleiche WebSocket allein stellt noch keine konsistente Verbindung zum LLM
her. `AgentSessionRunner._create_agent()` erstellt aktuell für jeden Run einen
eigenen `DeckStore` aus einem Snapshot der Session. Entfernt der Benutzer danach
über REST **oder RPC** einen Track, kennt der bereits laufende Agent diese
Änderung zunächst nicht.

Deshalb braucht es eine explizite Semantik. Empfohlen wird ein serieller
Session-Command-Stream („Session Actor“ oder per-Session Lock plus Mailbox):

```text
message.send -------+
track.remove -------+--> geordnete Session Commands --> Domain + Persistence
curation.restore ---+                |
                                      +--> Agent control mailbox
                                      +--> session.event publisher
```

Für den ersten produktiven Schnitt:

- alle mutierenden Session-Kommandos werden pro `session_id` serialisiert;
- die Domain-Session ist die kanonische Wahrheit;
- ein aktiver Agent erhält Playlist-/Curation-Änderungen über eine
  `SessionRunnerControl`-Schnittstelle bzw. Mailbox;
- Änderungen werden nur zwischen sicheren Agent-Schritten auf den internen
  `DeckStore` angewandt;
- ein bereits laufender LLM-Request kann nicht rückwirkend verändert werden;
  die Änderung gilt garantiert ab dem nächsten Model-/Tool-Schritt;
- das UI erhält nach Persistierung sofort das kanonische Playlist-Event.

Mögliches Port-Interface:

```python
class SessionRunnerControl(Protocol):
    async def apply_curation(
        self,
        *,
        session_id: UUID,
        run_id: UUID,
        change: SessionCurationChange,
    ) -> RunnerControlResult: ...
```

Alternativen müssen bewusst gewählt werden:

1. Mutationen während eines Runs ablehnen (`SessionBusy`) – einfach, aber
   schlechte UX.
2. Aktuellen Run stoppen und mit neuem Snapshot neu starten – konsistent, aber
   teuer und überraschend.
3. Änderungen nur persistieren und erst bei der nächsten User-Nachricht in den
   Agent-History-Builder aufnehmen – entspricht ungefähr dem heutigen Verhalten,
   ist aber nicht wirklich realtime.

Empfohlen ist Variante 3 für einen kleinen Protokoll-Spike und anschließend die
Mailbox-Variante. Die UI und der Contract sollten dabei schon `runId` und
`sessionRevision` führen, damit später keine Wire-Inkompatibilität entsteht.

## Event-Publisher und mehrere Connections

Benötigt wird ein Application-Port:

```python
class SessionEventPublisher(Protocol):
    async def publish(self, *, session_id: UUID, event: SessionEvent) -> None: ...
    def subscribe(self, *, session_id: UUID) -> AsyncIterator[SessionEvent]: ...
```

Der erste Adapter kann in-process arbeiten und Subscriber-Queues pro Session
halten. Er sollte von Anfang an Fan-out an mehrere Connections unterstützen.
Damit aktualisieren sich zwei Tabs konsistent und Resultat/Notification werden
nicht nur an den auslösenden Socket gekoppelt.

Für mehrere Backend-Instanzen reicht ein reiner In-Memory-Hub nicht. Dann wird
ein verteilter Adapter benötigt, zum Beispiel Redis Streams/PubSub oder Postgres
`LISTEN/NOTIFY` plus persistentes Event-/Revision-Log. Die Application-Schnittstelle
bleibt gleich.

Kanonische Domain-Events sollten transaktional mit dem Session-State committed
werden. Langfristig ist dafür ein Outbox-Pattern robuster als „DB speichern,
danach best effort publish“.

## Fehlerabbildung

Für jede erwartete Presentation-Exception wird eine stabile `RpcError`-Klasse
mit eigenem negativen Server-Code definiert. Beispielbereiche:

```text
-32001  authentication_required
-32002  session_not_found
-32003  session_access_denied
-32010  session_run_already_active
-32011  session_run_not_found
-32020  playlist_track_not_found
-32021  playlist_track_limit_exceeded
-32030  user_curation_event_not_found
-32031  user_curation_event_already_consumed
-32040  message_rate_limit_exceeded
```

Die konkrete Tabelle wird zentral in
`backend/features/session/presentation/rpc/errors.py` gepflegt. Der
`error_mapper` übersetzt bestehende Domain/Application Exceptions; unbekannte
Exceptions bleiben `Internal error` und werden nur serverseitig mit Traceback
geloggt.

Zu beachten: Der aktuelle `pyrpckit.RpcFailure`-Serverpfad überträgt nur `code`
und `message`, noch keine strukturierten Error-Details. Feldfehler oder
Retry-After können daher zunächst nur stabil über Code/Message modelliert werden
oder benötigen eine kleine Erweiterung in `pyrpckit`.

## OpenRPC und Codegenerierung

Der Contract wird im Backend definiert:

```python
SESSION_RPC_CONTRACT = OpenRpcContract(
    app=RPC_APP,
    title="Prompster Session RPC",
    servers=(
        OpenRpcServer(
            name="session-channel",
            url="wss://{host}/api/v1/sessions/{sessionId}/rpc",
            variables={
                "host": ServerVariable(default="localhost:8000"),
                "sessionId": ServerVariable(default="00000000-0000-0000-0000-000000000000"),
            },
            extensions={
                "x-rpckit-transport": {
                    "type": "websocket",
                    "messageEncoding": "json",
                    "subprotocols": ["prompster.rpc.v1"],
                }
            },
        ),
    ),
)
```

Ob der derzeitige Endpoint-Resolver frei gesetzte `sessionId`-Variablen beim
`connect()` ergonomisch genug unterstützt, ist im Spike zu verifizieren. Falls
nicht, wird der `WebSocketTransport` mit der bereits aufgelösten URL erzeugt und
an `PrompsterSessionClient.fromTransport()` übergeben. Das Protokoll selbst muss
dafür nicht geändert werden.

Build-Schritte:

```bash
pyrpckit schema backend.src.backend.features.session.presentation.rpc.contract:SESSION_RPC_CONTRACT \
  --output frontend/session.openrpc.json

pyrpckit generate frontend/session.openrpc.json \
  --language typescript \
  --output frontend/src/api/rpc/generated \
  --client-name PrompsterSessionClient \
  --transport-module ../transport
```

Die genauen Python-Modulpfade sind an das `uv`-Workspace-Setup anzupassen. In CI
laufen beide Befehle zusätzlich mit `--check`. Generierte Dateien werden
committed, aber nie manuell editiert.

Empfohlene Trennung im Frontend:

```text
frontend/src/api/rpc/
  generated/          # vollständig von pyrpckit erzeugt
  transport.ts        # zunächst aus Generator-Template übernommen/angepasst
  session-channel.ts  # Reconnect, Auth-/URL-Konfiguration, Lifecycle
```

Der aktuelle pyrpckit-TypeScript-Transport:

- korreliert parallele Requests über numerische IDs;
- liefert Notifications als `AsyncIterable`;
- unterstützt Request-Timeout und bounded Notification Queue;
- besitzt aktuell **keinen automatischen Reconnect**, kein Replay und keine
  Command-Deduplizierung;
- beendet bei Socketfehlern alle Pending Requests und Notification-Iteratoren.

Reconnect gehört daher in `session-channel.ts` oder später als wiederverwendbare
Erweiterung zurück in `pyrpckit`. Handgeschriebene Änderungen innerhalb des
generierten Verzeichnisses wären beim nächsten Generate verloren.

## Frontend-Integration

`useChatSession` erhält einen einzigen Channel-Lifecycle:

```typescript
const channel = await SessionChannel.open(sessionId);
const events = channel.client.session.event();
const consumeEvents = consumeSessionEvents(events, dispatch);
const synced = await channel.client.session.sync({});
dispatch({ type: "session/loaded", session: synced.session });
```

Wichtig ist die Reihenfolge: erst Notification-Subscription registrieren, dann
`sync` aufrufen. Andernfalls kann zwischen Snapshot und Subscription eine
Änderung verloren gehen. `sessionRevision` schließt auch dieses kleine
Race-Fenster: Events bis zur Snapshot-Revision werden ignoriert, eine Lücke löst
einen erneuten Sync aus.

Danach ersetzen generierte Methoden:

```typescript
await client.session.message.send({...});
await client.session.message.stop({ runId, commandId });
await client.session.playlist.track.remove({ trackId, commandId });
await client.session.curationEvent.restore({ eventId, commandId });
```

Folgende heutige Sonderlogik entfällt:

- manueller `fetch()`-SSE-Parser in `session-stream.ts`;
- `AbortController` als primärer Stop-Mechanismus;
- Refetch der kompletten Session nach Track-Entfernen/-Hinzufügen und Restore;
- Schema-only HTTP-Routen ausschließlich für Event-Codegen;
- parallele handgeschriebene Eventtypen neben dem generierten Client.

Der bestehende `chat-reducer.ts` kann erhalten bleiben und auf die generierte
`SessionRpcEvent`-Union umgestellt werden. Zusätzlich benötigt er:

- `activeRunId` und Run-Status;
- zuletzt angewandte `sessionRevision`;
- Event-Deduplizierung;
- `connectionState`: `connecting | connected | reconnecting | offline`;
- klare Trennung von Command-Fehlern und Run-Fehlern.

Beim Wechsel auf einen anderen `session_id` wird der alte Client geschlossen,
alle Consumer-Tasks werden beendet und erst dann der neue Channel aufgebaut.
React Strict Mode und schnelle Navigation müssen durch Tests abgedeckt werden,
damit keine doppelten Sockets oder doppelten `message.send`-Kommandos entstehen.

## Welche bestehenden HTTP-Endpunkte wohin wandern

| Heutiger Endpunkt | Ziel | Begründung |
| --- | --- | --- |
| `POST /{id}/messages` | RPC `session.message.send` | startet asynchronen Run |
| `POST /{id}/onboarding/complete` | RPC `session.onboarding.complete` | startet asynchronen Run |
| `POST /{id}/messages/stop` | RPC `session.message.stop` | Steuerkommando auf aktivem Kanal |
| `POST /{id}/onboarding-answer` | RPC `session.onboarding.answer.submit` | interaktiver Channel-State |
| `POST /{id}/tracks` | RPC `session.playlist.track.add` | kanonisches Event statt Refetch |
| `POST /{id}/tracks/spotify` | RPC `session.playlist.track.addSpotify` | kanonisches Event statt Refetch |
| `DELETE /{id}/tracks/{track_id}` | RPC `session.playlist.track.remove` | Curation + Agent-Synchronität |
| `POST /{id}/curation-events/{event_id}/restore` | RPC `session.curationEvent.restore` | Curation + Agent-Synchronität |
| `GET /{id}` | RPC `session.sync` im offenen Channel | Snapshot/Reconnect; REST vorerst kompatibel halten |
| `PATCH /{id}`, star/unstar | zunächst REST, optional später RPC | kein Agent-Streaming-Bezug |
| `DELETE /{id}` | REST | zerstörerischer Lifecycle außerhalb des Channels; bei Delete Socket schließen |
| `GET /{id}/playlist/pdf` | HTTP | Binärdownload |
| `POST /{id}/playlist/spotify` | vorerst HTTP/SSE, später eigener RPC-Job | externer langer Export, eigener Job-Lifecycle sinnvoll |
| Image-Attachment-Upload | HTTP | Binär-/Multipart-Transport |

Für einen konsequenten Channel kann `PATCH`, star/unstar später ebenfalls als RPC
angeboten werden. Für den ersten Spike erhöht das die Aussagekraft über das
Agent-Protokoll nicht.

## Konkrete Backend-Dateien und Änderungen

Neu:

```text
backend/src/backend/features/session/presentation/rpc/
  __init__.py
  router.py             # RpcRouter und dekorierte SessionRpcMethods
  models.py             # Params, Results, SessionRpcEvent union
  errors.py             # RpcError-Klassen und error_mapper
  mapper.py             # Application SessionEvent -> SessionRpcEvent
  contract.py           # RpcApp und OpenRpcContract
  websocket.py          # FastAPI-Adapter, Reader/Writer/Backpressure

backend/src/backend/features/session/application/
  session_run_coordinator.py
  ports/session_event_publisher.py
  ports/session_runner_control.py   # erst ab Live-Curation-Ausbaustufe

backend/src/backend/features/session/infrastructure/
  in_memory_session_event_publisher.py
  session_run_coordinator.py        # falls Task-/Runtime-Details als Infra gelten
```

Anpassen:

- `features/session/__init__.py`: WebSocket-Router und Provider registrieren.
- `features/session/infrastructure/di.py`: Publisher, Coordinator und kurzlebige
  Service-/UoW-Factories bereitstellen; keinen DB-Request-Scope am Socket halten.
- `application/conversation_service.py`: fachliche Verarbeitung und Eventerzeugung
  behalten, aber AsyncIterator-Konsum vom HTTP-Response entkoppeln.
- `application/ports/session_runner.py`: `run_id`/Control-Semantik ergänzen, ohne
  RPC-Typen einzuführen.
- `infrastructure/session_runner.py`: Runtime Registry um adressierbare Runs und
  später Control-Mailbox ergänzen.
- `presentation/sse/mappers.py`: Mappinglogik in transportneutralen bzw.
  RPC-spezifischen Mapper verschieben; während Migration SSE delegieren lassen.
- `presentation/router.py`: alte Endpunkte während Rollout behalten und danach
  gezielt entfernen.
- `main.py`/Feature-Komposition: WebSocket-Route und ggf. Origin-Policy aufnehmen.
- Migration/ORM: `session_revision`, persistenter Run-Status und Command-Dedupe;
  für den reinen Spike kann ein In-Memory-Teil bewusst markiert werden.

Der Agent in `libs/agent` muss für den ersten Transport-Spike nicht geändert
werden. Erst für garantiert live wirksame Playlist-Mutationen braucht er eine
sichere Control-/Mailbox-API rund um seinen `DeckStore`. Diese API bleibt lokal
und kennt kein `pyrpckit`.

## Konkrete Frontend-Dateien und Änderungen

Neu:

```text
frontend/session.openrpc.json
frontend/src/api/rpc/generated/**
frontend/src/api/rpc/transport.ts
frontend/src/api/rpc/session-channel.ts
```

Anpassen:

- `features/chat/hooks/use-chat-session.ts`: einen Socket pro geöffneter Session,
  generierte Commands, Reconnect und Sync verwenden.
- `features/chat/state/chat-reducer.ts`: generierte Event-Union, Revision und
  Run-ID verarbeiten.
- Deck-/Curation-Komponenten: RPC-Commands statt Orval-Mutations plus Refetch.
- `package.json`: `generate:rpc` und `check:rpc` Scripts ergänzen.
- CI: OpenRPC-Schema und TypeScript-Client mit `--check` validieren.

Nach stabiler Migration entfernen:

- `features/chat/api/session-stream.ts`;
- nicht mehr benötigte SSE-Schema-Hilfsrouten;
- SSE-spezifische Event-Endmarker;
- Orval-Ausgaben und Hooks für die migrierten Session-Mutationen.

## Reconnect- und Recovery-Protokoll

Minimaler Algorithmus:

1. Socket mit Cookie und Subprotocol öffnen.
2. `session.event` abonnieren.
3. `session.sync({afterRevision: lastRevision})` aufrufen.
4. Snapshot anwenden oder, falls echtes Replay vorhanden ist, fehlende Events
   in Revision-Reihenfolge anwenden.
5. Pending Command mit derselben `commandId` nur dann erneut senden, wenn sein
   Status unbekannt ist.
6. Bei Timeout zuerst `session.run.get` bzw. Command-Status prüfen, nicht blind
   duplizieren.
7. Reconnect mit exponentiellem Backoff und Jitter; bei Auth-Fehler Access Token
   über den bestehenden HTTP-Refresh erneuern und dann neu verbinden.

Ein Snapshot ist für den ersten Spike ausreichend, weil persistierte Nachrichten
und Playlist daraus wieder aufgebaut werden können. Ephemere Events wie Retry-
Countdowns oder einzelne Chunks können dabei verloren gehen. Produktiv sauber
wird es erst mit persistierter Revision und begrenztem Event-Replay.

## Tests

### Contract und Codegen

- OpenRPC-Snapshot enthält jede Methode, Notification, Union und declared error.
- `pyrpckit schema --check` erkennt Contract-Drift.
- `pyrpckit generate --check` erkennt Client-Drift.
- camelCase, UUID, optionale Felder und alle `type`-Literale roundtrippen.

### WebSocket-Adapter

- Auth fehlt/ist abgelaufen/hat keinen Session-Zugriff.
- mehrere parallele Requests erhalten die richtige Response-ID.
- Notifications und Responses werden ohne konkurrierende `send_json`-Aufrufe
  geschrieben.
- `message.stop` wird während laufender Events verarbeitet.
- malformed JSON, invalid params, unbekannte Methode und interne Exception werden
  als korrekte JSON-RPC Errors geliefert.
- langsamer Client löst definierte Backpressure-Policy aus.
- Disconnect räumt Subscriber und Request-Tasks auf, lässt akzeptierten Run aber
  entsprechend der Policy weiterlaufen.

### Run-Lifecycle

- genau ein aktiver Conversation-Run pro Session.
- `commandId` verhindert doppelte User-Nachrichten.
- Run läuft nach Socketverlust weiter und wird nach Reconnect synchronisiert.
- Stop adressiert den erwarteten `runId` und stoppt keinen neueren Run.
- terminaler Status wird auch ohne Client persistiert.
- Backend-Neustart markiert/verarbeitet liegengebliebene Runs deterministisch.

### Session-Mutationen

- Track-Remove und Restore senden genau ein kanonisches Event an jeden Subscriber.
- ein zweiter Tab aktualisiert sich ohne Refetch.
- Event-Reihenfolge und Revision bleiben bei parallelen Commands stabil.
- Mutationen während eines Runs folgen der dokumentierten Spike-/Mailbox-Semantik.

### Frontend

- Mount/Unmount und React Strict Mode erzeugen keinen Socket-Leak.
- Session-Wechsel mischt keine Events verschiedener Sessions.
- Reconnect führt nicht zu doppelten Reducer-Änderungen.
- Command-Fehler, Run-Fehler und Offline-State werden getrennt angezeigt.
- Notification-Queue-Fehler führt zu Reconnect und Sync.

## Rollout in Etappen

### Etappe 1: Protokoll-Spike

- `session.sync`, `session.message.send`, `session.message.stop` und
  `session.event` implementieren.
- In-Memory Publisher, ein Backend-Worker, Snapshot-Reconnect.
- SSE parallel als Fallback behalten.
- Metriken und Contract-/Roundtrip-Tests ergänzen.

Erfolgskriterium: Ein Agent-Run kann gestartet, live verfolgt, gestoppt und nach
Socket-Unterbrechung per Snapshot wieder aufgenommen werden.

### Etappe 2: Channel-Mutationen

- Onboarding, Track Add/Remove und Curation Restore auf RPC umstellen.
- `commandId`, `sessionRevision` und Fan-out an mehrere Tabs aktivieren.
- Frontend-Refetches entfernen.
- Verhalten von Änderungen während eines Agent-Runs zunächst explizit als
  „wirksam ab nächstem Run/Schritt“ dokumentieren.

### Etappe 3: Agent-Control und Produktion

- per-Session Command-Serialisierung und Agent-Control-Mailbox.
- persistenter Event-/Revision-Log oder Outbox.
- verteilter Publisher für mehrere Backend-Instanzen.
- Restart-Recovery, Proxy-Timeouts, Heartbeats, Last- und Chaos-Tests.
- SSE-Endpunkte und Schema-Workarounds entfernen.

## Offene Punkte, die im Spike beantwortet werden müssen

1. Soll genau ein Conversation-Run pro Session oder pro Connection erlaubt sein?
   Empfehlung: pro Session.
2. Soll ein Run ohne Client unbegrenzt weiterlaufen oder nach einem Timeout
   beendet werden? Empfehlung: zunächst weiterlaufen, mit globalem Run-Timeout.
3. Reicht Snapshot-Recovery oder werden Token-/Tool-Events lückenlos benötigt?
4. Werden mehrere Backend-Worker bereits im ersten Deployment genutzt? Dann ist
   ein In-Memory Publisher nur mit Sticky Sessions vertretbar.
5. Welche Semantik gilt für Playlist-Mutationen während eines bereits laufenden
   LLM-Requests? Empfehlung: Persistierung sofort, garantierte Agent-Wirkung ab
   nächstem sicheren Schritt.
6. Soll der Spotify-Export ein eigener RPC-Job mit Notifications werden? Das ist
   sinnvoll, aber getrennt vom Conversation-Spike zu behandeln.

## Abnahmekriterien für die Gesamtintegration

- Innerhalb einer geöffneten Session existiert nur ein langlebiger Client-Kanal.
- Alle Conversation- und Curation-Kommandos sind typisierte, generierte
  RPC-Methoden.
- Alle Live-Updates kommen als generierte, discriminated `session.event`-Union.
- Kein handgeschriebener SSE-Parser und kein Refetch nach Track-Remove/Restore.
- Disconnect und Reconnect erzeugen weder doppelte Nachrichten noch verlorenen
  kanonischen Session-State.
- Ein Stop-Kommando ist während eines laufenden Runs erreichbar.
- Der Agent-Run besitzt eine vom WebSocket unabhängige `run_id` und Lebensdauer.
- `pyrpckit` taucht nur im Presentation Layer und in Build-/Codegen-Konfiguration
  auf; Application, Domain und Agent bleiben transportagnostisch.
- Multi-Connection-Fan-out, Backpressure, Fehlerabbildung und Auth sind getestet.
- Die Semantik von Live-Curation gegenüber dem Agent-`DeckStore` ist nicht nur
  implizit, sondern technisch durch Serialisierung/Mailbox oder bewusst
  dokumentierte Übergangsregeln abgesichert.

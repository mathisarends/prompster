# LLM Selection (Backend + Frontend) — Implementierungsplan

## Ziel

Der User soll im Chat-UI (Home + Chat-Page) zwischen verschiedenen OpenAI-Modellen
(`gpt-5.4`, `gpt-5.4-mini`, `gpt-5.5`) wählen können. Die Auswahl steuert, welches
Modell der Agent (`AgentSessionRunner`) pro Turn verwendet. Die Selektion wird auf
der Session persistiert, damit sie über Reloads hinweg stabil bleibt und in der
Session-History rekonstruierbar ist.

## Status Quo

- `llm/src/llm/registry.py` listet die unterstützten Modelle (`OpenAIModelName`)
  inklusive Default `GPT_5_4_MINI`.
- `llm/src/llm/factory.py` exponiert `create_openai_llm(model=...)` plus
  Convenience-Funktionen pro Modell.
- `SessionProvider` (`backend/src/backend/features/session/infrastructure/di.py`)
  baut **eine** `ChatModel`-Instanz auf APP-Scope und injiziert sie in
  `AgentSessionRunner`. Modellwahl ist damit derzeit hart auf `gpt-5.4` verdrahtet.
- `AgentSessionRunner.run(session=...)` nimmt nur die Session, kein Modell.
- `SendMessageRequest` / `FollowUpRequest` enthalten kein Modell-Feld.
- Frontend `ChatInputBox` schickt nur den Textinhalt; Home-Page erzeugt die Session
  über `createSession({ initialPrompt })` ohne Modell.

## Designentscheidungen

### 1. Persistenz auf der Session, Override pro Turn

- Jede `Session` bekommt ein Feld `selected_model: OpenAIModelName`. Default
  zur Erstellung = `DEFAULT_OPENAI_MODEL`.
- Beim Senden einer Nachricht / Beantworten von Follow-Ups darf optional ein
  abweichendes Modell mitgegeben werden (`model: OpenAIModelName | None`). Wird
  es übergeben, wird `session.selected_model` aktualisiert _und_ der Turn mit dem
  neuen Modell ausgeführt — UI-State und Backend-State bleiben so synchron.
- Vorteil ggü. „nur per-Turn": HistoryView / Resume nach Refresh weiß weiterhin,
  welches Modell der Chat zuletzt benutzt hat → der Picker im Frontend zeigt
  konsistenten Wert ohne Extra-Logik im LocalStorage.

### 2. LLM-Factory in der DI

- Statt einer einzelnen `ChatModel`-Singleton-Instanz exponieren wir einen
  `ChatModelFactory`-Port (callable `(OpenAIModelName) -> ChatModel`).
- `SessionProvider` registriert die Factory als APP-Scope. `AgentSessionRunner`
  und `LLMSessionTitleGenerator` rufen die Factory pro Turn / pro Aufruf mit
  dem gewünschten Modell auf.
- Caching der erzeugten Instanzen erfolgt im Factory-Implementierungsdetail
  (`functools.lru_cache` über Modellname). Damit bleibt der Speicherverbrauch
  klein und Verbindungen werden wiederverwendet.

### 3. Title-Generator bleibt auf festen Default

- Der `LLMSessionTitleGenerator` wird absichtlich nicht vom User-Picker
  gesteuert. Er nutzt weiterhin `DEFAULT_OPENAI_MODEL` (= `gpt-5.4-mini`), das
  ist günstig und genügt für Titelgenerierung.

---

## Backend-Implementierung

### Schritt 1 — LLM-Paket: Factory-Port

Neue Datei `llm/src/llm/factory_port.py`:

```python
from typing import Protocol
from llmify import ChatModel
from llm.registry import OpenAIModelName

class ChatModelFactory(Protocol):
    def __call__(self, model: OpenAIModelName) -> ChatModel: ...
```

Export in `llm/src/llm/__init__.py` ergänzen.

Konkrete Implementierung dort als `create_chat_model_factory(credentials)`:

```python
def create_chat_model_factory(credentials: LLMCredentials) -> ChatModelFactory:
    @lru_cache(maxsize=len(OPENAI_MODELS))
    def factory(model: OpenAIModelName) -> ChatModel:
        return create_openai_llm(model=model, credentials=credentials)
    return factory
```

### Schritt 2 — Domain & Repository

- `Session.__init__` erweitern um `selected_model: OpenAIModelName`
  (Default `DEFAULT_OPENAI_MODEL`). Getter + `change_selected_model(model)`-Methode.
- `Session.create_with_initial_prompt(..., selected_model: OpenAIModelName)`
  zusätzliche Pflichtparameter.
- `SessionModel` (ORM, `backend/src/backend/infrastructure/database/orm.py`):
  Feld `selected_model: str` (string, kein Enum, damit zukünftige Modelle ohne
  DB-Schema-Änderung registriert werden können). Default Server-Side via
  `server_default=text("'gpt-5.4-mini'")`.
- Alembic-Migration `0006_add_session_selected_model.py`:
  `op.add_column("sessions", sa.Column("selected_model", sa.String(length=64), nullable=False, server_default=text("'gpt-5.4-mini'")))`.
- `SqlSessionRepository._to_domain` / `save`: das Feld mappen, beim Lesen
  durch `ensure_supported_openai_model` validieren (so wird ein in der DB
  gelandetes, mittlerweile unbekanntes Modell auf einen Fehler oder einen
  Fallback gemappt — Entscheidung: **Fallback auf Default + Log-Warning**, damit
  alte Sessions nie blocken).

### Schritt 3 — DI-Container

`backend/src/backend/features/session/infrastructure/di.py` anpassen:

```python
@provide(scope=Scope.APP)
def provide_chat_model_factory(self, credentials: LLMCredentials) -> ChatModelFactory:
    return create_chat_model_factory(credentials)

@provide(scope=Scope.APP)
def provide_title_generator_llm(self, factory: ChatModelFactory) -> ChatModel:
    return factory(DEFAULT_OPENAI_MODEL)

@provide(scope=Scope.APP)
def provide_session_runner(
    self,
    factory: ChatModelFactory,
    spotify: Spotifyify,
) -> SessionRunner:
    return AgentSessionRunner(chat_model_factory=factory, spotify=spotify)
```

### Schritt 4 — SessionRunner-Port

`backend/src/backend/features/session/application/ports/session_runner.py`:

- `SessionRunner.run(*, session: Session, model: OpenAIModelName) -> AsyncIterator[...]`
  (zweites Pflichtargument).

`AgentSessionRunner`:

```python
class AgentSessionRunner(SessionRunner):
    def __init__(
        self,
        chat_model_factory: ChatModelFactory,
        spotify: Spotifyify,
        system_prompt: str | None = None,
    ) -> None:
        self._chat_model_factory = chat_model_factory
        ...

    async def run(self, *, session: Session, model: OpenAIModelName):
        llm = self._chat_model_factory(model)
        agent = Agent(llm=llm, ...)
        ...
```

### Schritt 5 — ConversationService

`SessionConversationService`:

- `send_message(..., model: OpenAIModelName | None = None)`
  - Wenn `model is not None`: `session.change_selected_model(model)`.
  - `await self._runner.run(session=session, model=session.selected_model)`.
- Gleiches Pattern für `answer_follow_ups` und `skip_remaining_follow_ups`.
- `_run_agent(session=..., model=...)` als Helper, der das Modell an den Runner
  weitergibt.

### Schritt 6 — SessionService (für initial-create)

`SessionService.create(..., selected_model: OpenAIModelName)`:

- `Session.create_with_initial_prompt(..., selected_model=selected_model)`.
- Validierung des Strings über `ensure_supported_openai_model` direkt im
  Presentation-Layer, bevor das Domain-Objekt erstellt wird.

### Schritt 7 — Presentation (FastAPI)

Neuer Endpoint **`GET /llms`** (eigener Router `llms_router` unter `backend/features/llm`):

```python
class LLMOptionResponse(Schema):
    id: str          # z.B. "gpt-5.4-mini"
    label: str       # z.B. "GPT-5.4 mini"
    description: str # kurze Beschreibung für die UI
    is_default: bool

class LLMOptionsResponse(Schema):
    options: list[LLMOptionResponse]
    default: str
```

- Statische Liste, abgeleitet aus `OPENAI_MODELS`. Labels/Descriptions als Dict in
  `backend/features/llm/presentation/catalog.py` pflegen.
- Auth-pflichtig (gleiche `AuthenticatedUserId`-Dependency).

Schemas in `session/presentation/schemas.py` erweitern:

- `SessionResponse.selected_model: str`.
- `SessionCreateRequest.selected_model: str | None = None`.
- `SessionUpdateRequest.selected_model: str | None = None` (optional ändern ohne
  Nachricht zu senden — z.B. user wechselt Modell direkt nach Session-Erstellung
  ohne neue User-Message).
- `SendMessageRequest.model: str | None = None`.
- `FollowUpRequest.model: str | None = None`.

Mapper:

- `to_session_response` ergänzt `selected_model=session.selected_model.value`.

Router (`session/presentation/router.py`):

- `create_session`: leitet `body.selected_model` weiter (via
  `ensure_supported_openai_model` oder Fallback auf Default bei `None`).
- `send_message` / `handle_follow_up`: gibt `body.model` an den Service weiter.
- `update_session`: erlaubt Setzen von `selected_model` ohne Title-Pflicht
  (`SessionUpdateRequest` muss `model_validator` bekommen, dass mindestens ein
  Feld gesetzt ist).

### Schritt 8 — Validierung & Fehlerbehandlung

- Pydantic-Schema akzeptiert nur Strings; tatsächliche Whitelist-Prüfung im
  Service-Layer via `ensure_supported_openai_model`. `ValueError` wird durch den
  bestehenden Exception-Handler in `session/presentation/exception_handlers.py`
  zu `400 Bad Request` (neuer Handler nötig, falls noch nicht vorhanden).

### Schritt 9 — Tests (Backend)

- Unit-Tests `Session`-Aggregate: Default-Modell, `change_selected_model`.
- Unit-Tests `SessionConversationService`: Wenn `model` mitgegeben, wird Session
  aktualisiert; Runner bekommt das richtige Modell.
- Integration-Test Repository: Modell wird persistiert und beim Laden zurückgegeben.
- API-Test `POST /sessions/{id}/messages` mit `model: "gpt-5.5"` → SessionResponse
  zeigt das neue Modell.
- API-Test `GET /llms` → Liste aller Modelle, Default markiert.

---

## Frontend-Implementierung

### Schritt 10 — OpenAPI-Regenerierung

Nach Backend-Änderungen das vorhandene Skript zur Generierung von
`frontend/src/api/generated/**` ausführen (orval o.ä. — Befehl siehe `package.json`).
Neue Typen tauchen automatisch auf:

- `LLMOptionResponse`, `LLMOptionsResponse`
- `SessionResponse.selectedModel`
- `SendMessageRequest.model`
- `SessionCreateRequest.selectedModel`
- `SessionUpdateRequest.selectedModel`

### Schritt 11 — LLM-Liste laden

Neuer Hook `frontend/src/hooks/useAvailableLlms.ts`:

```ts
export const useAvailableLlms = () => {
  return useQuery({
    queryKey: ["llms"],
    queryFn: getAvailableLlms,
    staleTime: Infinity,
  });
};
```

- Daten cachen, nicht refetchen — die Liste ändert sich nur bei Deploys.

### Schritt 12 — LLM-Picker-Komponente

Neue Komponente `frontend/src/components/chat/llm-picker.tsx`:

- Wrapped `DropdownMenu` aus `components/ui/dropdown-menu.tsx`.
- Props: `value: string`, `onChange: (model: string) => void`, `disabled?: boolean`.
- Trigger ist ein kompakter Button mit Modell-Label + Chevron-Icon (Lucide).
- Liste zeigt Label (fett) + Description (muted) je Option.
- Aktive Option per Checkmark markiert.

Style: dezent, passt in die `ChatInputBox` (linke untere Ecke neben dem Send-Button).

### Schritt 13 — Integration in `ChatInputBox`

- Optionale Props ergänzen:
  ```ts
  selectedModel?: string;
  onModelChange?: (model: string) => void;
  ```
- Wenn beide gesetzt sind, wird der `LlmPicker` unter dem Textarea-Feld
  (im Single-Line wie Multi-Line Modus) gerendert. Ansonsten bleibt das Verhalten
  unverändert (rückwärtskompatibel).
- Mockup:
  ```
  ┌────────────────────────────────────────────┐
  │  Deine Antwort ...                         │
  │                                            │
  │  [GPT-5.4 mini ▾]              [➤ Senden]  │
  └────────────────────────────────────────────┘
  ```

### Schritt 14 — Home-Page

- `HomePage` lädt `useAvailableLlms()` und hält `selectedModel`-State,
  initialisiert mit `data.default`.
- Persistenz in `localStorage` via `useLocalStorage("prompster.selectedLlm", ...)`,
  damit der User über Sessions hinweg seinen bevorzugten Default behält.
  Wenn vorhandener Wert nicht (mehr) in der Server-Liste ist → auf Default
  zurückfallen.
- `startChat` ruft `createSession({ initialPrompt: text, selectedModel })`.
- `LlmPicker` über die neuen Props in `ChatInputBox` aktiv.

### Schritt 15 — Chat-Page

- `useChatSession` (`frontend/src/pages/chat-page.hook.ts`) gibt
  `session.selectedModel` zurück. Lokaler State `selectedModel` mit Initialwert
  aus der Session, fällt zurück auf den localStorage-Wert / `default` bevor die
  Session geladen ist.
- Beim Senden einer Nachricht wird `model: selectedModel` mit übergeben.
- Wenn der User das Modell ändert _ohne_ eine Nachricht zu senden, optional via
  `updateSession({ sessionId, selectedModel })` debounced persistieren (damit
  Reload den Wert behält). MVP: Wir können diesen Call weglassen und das Modell
  erst beim nächsten `sendMessage` mitschicken — einfacher, kein extra Endpoint
  pingen. **Empfehlung MVP: nur über `sendMessage` persistieren.**

### Schritt 16 — Reaktion auf Antwort

- Backend gibt nach jedem `sendMessage` Stream-Antworten und beim nachfolgenden
  `GET /sessions/{id}` das neue `selectedModel` zurück → React-Query
  invalidiert die Session, die UI synchronisiert sich automatisch.

### Schritt 17 — Disabled-States

- `LlmPicker` wird disabled, wenn `isStreaming === true` oder
  `isLoadingSession === true` (kein Modellwechsel mitten im laufenden Turn).
- Tooltip auf dem Picker: „Modell für den nächsten Turn".

### Schritt 18 — Frontend-Tests

- Component-Test `LlmPicker`: rendert alle Optionen, Klick triggert `onChange`.
- Component-Test `ChatInputBox`: Picker wird nur gezeigt, wenn Props gesetzt.
- Hook-Test `useAvailableLlms`: Default-Fallback funktioniert, wenn localStorage
  unbekanntes Modell enthält.

---

## Reihenfolge / Risiken

1. **Erst Backend, dann Frontend.** Frontend hängt am generierten Client.
2. **Migration zuerst**, danach Code mergen — sonst kracht es lokal beim
   Hochfahren der App.
3. **Title-Generator nicht versehentlich mitkoppeln.** Klare Trennung über zwei
   separate `provide_*`-Funktionen in der DI.
4. **Backwards-Compat**: `SendMessageRequest.model` ist optional. Alte Clients
   funktionieren weiter (Backend nutzt `session.selected_model` als Fallback).
5. **Validierung Whitelist** muss konsequent vor Erreichen des Domain-Layers
   erfolgen, damit ein manipulierter Request keinen ungültigen `OpenAIModelName`
   in die DB schreibt.

## Out of Scope

- Anthropic-/andere Provider — `registry.py` ist OpenAI-only. Erweiterung später
  durch zusätzliche `Provider`-Enums und Diskriminator-Logik im Factory.
- Pro-User-Default in der DB (z.B. „User XY bevorzugt gpt-5.5"). MVP nutzt
  localStorage am Frontend.
- Kostenanzeige / Token-Counter pro Modell.

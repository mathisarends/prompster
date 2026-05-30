# Implementation Plan: ask_onboarding_question

## Ziel

Ein neues Tool `ask_onboarding_question` für die Onboarding-Phase, das:
- **Eine Frage auf einmal** stellt (3–5×, dynamisch generiert)
- Nach jeder Frage **pausiert** bis der User geantwortet hat
- Danach eine **statische Abschlussfrage** stellt ("Welche Playlists?") über einen anderen Mechanismus
- Alle Fragen + Antworten **in der DB speichert**
- Dem Agent die Antworten als **formatierten String** exposes

---

## 1. Persistenzkonzept

### Neue Tabelle: `SessionOnboardingQuestionModel`

```python
class SessionOnboardingQuestionModel(DatabaseEntity, table=True):
    session_id: UUID                  # FK → SessionModel
    sequence_number: int              # Reihenfolge der Fragen
    question_text: str
    options: list[str]                # JSON array, kann [] sein (free-text only)
    answer: str | None = None         # Antwort: gewählte Option ODER Freitext
    is_answered: bool = False
    answered_at: datetime | None = None
```

**Warum als eigene Tabelle?** Die Fragen haben einen eigenen Lifecycle (pending → answered) und müssen geordnet ausgelesen werden. Sie sind kein Message-Typ, sondern strukturiertes Session-State.

### Alembic-Migration

Neue Revision `add_onboarding_questions_table`.

---

## 2. Domain-Darstellung

### Neues Entity: `OnboardingQuestion`

```python
class OnboardingQuestion(Entity):
    sequence_number: int
    question_text: str
    options: list[str]         # leer = nur Freitext
    answer: str | None = None
    is_answered: bool = False
```

### Session Aggregate – Erweiterung

```python
class Session(Aggregate):
    # ... bestehende Felder ...
    onboarding_questions: list[OnboardingQuestion] = []

    def add_onboarding_question(self, question_text: str, options: list[str]) -> OnboardingQuestion:
        seq = len(self.onboarding_questions) + 1
        q = OnboardingQuestion(sequence_number=seq, question_text=question_text, options=options)
        self.onboarding_questions.append(q)
        return q

    def answer_onboarding_questions(self, answers: dict[UUID, str]) -> None:
        """Beantwortet mehrere Fragen auf einmal – alle answers in einem Aufruf."""
        for q in self.onboarding_questions:
            if q.id in answers:
                q.answer = answers[q.id]
                q.is_answered = True

    def get_answered_onboarding_context(self) -> str:
        """Formatierter String für Agent-Kontextinjektion."""
        answered = [q for q in self.onboarding_questions if q.is_answered]
        if not answered:
            return ""
        lines = ["=== Beantwortete Onboarding-Fragen ==="]
        for q in answered:
            lines.append(f"{q.sequence_number}. {q.question_text}")
            lines.append(f"   → {q.answer}")
        return "\n".join(lines)
```

---

## 3. Agent-Darstellung

### Kontextinjektion (wie Playlist-State heute)

`MessageManager` injiziert vor jedem LLM-Request einen Block mit den beantworteten Fragen:

```
=== Beantwortete Onboarding-Fragen ===
1. Für wen ist die Playlist?
   → Familie mit Kindern (8–12 Jahre)

2. Welche Jahrzehnte sollen dominieren?
   → 80er und 90er

3. Wie breit soll das Genre-Spektrum sein?
   → Fokussiert – hauptsächlich Pop und Soft Rock
```

Das sieht für das LLM wie ein normaler Kontext-String aus – keine strukturierten Objekte, keine Tool-Ergebnisse.

---

## 4. Neues Tool: `ask_onboarding_question`

### Params

```python
class AskOnboardingQuestionParams(ToolParams):
    status: str = "Stelle Onboarding-Frage..."
    question: str           # Die zu stellende Frage
    options: list[str]      # 2–4 Optionen; darf auch Freitext-Option enthalten
```

### Registrierung

```python
@tools.action(
    description=(
        "Stelle dem User eine einzelne Klärungsfrage während des Onboardings. "
        "Rufe dieses Tool einmal pro Frage auf. Der Agent pausiert, bis der User geantwortet hat."
    ),
    params=AskOnboardingQuestionParams,
    status_label=lambda p: p.status,
    action_type=ActionType.INTERACT,    # neuer ActionType
    included_in_phases={Phase.ONBOARDING},
    suspends_for_input=True,            # neues Flag auf Tool
)
async def ask_onboarding_question(
    session: Inject[Session],
    params: AskOnboardingQuestionParams,
) -> ActionResult:
    session.add_onboarding_question(
        question_text=params.question,
        options=params.options,
    )
    return ActionResult(
        success=True,
        extracted_content=f"Frage gestellt: {params.question}",
        suspend=True,                   # neues Feld auf ActionResult
    )
```

### Erweiterung `ActionType`

```python
class ActionType(StrEnum):
    SEARCH = "search"
    FETCH = "fetch"
    MUTATE = "mutate"
    INTERACT = "interact"   # NEU: pausiert für User-Input
```

---

## 5. Suspension-Mechanismus

### Erweiterung `ActionResult`

```python
class ActionResult(BaseModel):
    success: bool
    extracted_content: str = ""
    error: str | None = None
    suspend: bool = False   # NEU: Agent bricht Run-Loop ab
```

### Agent Loop-Modifikation (`agent.py`)

```python
async def _run_loop(self):
    while True:
        response = await self._stream_llm_response()
        if not response.tool_calls:
            break

        for tool_call in response.tool_calls:
            result = await self._handle_tool_call(tool_call)

            if result.suspend:                         # NEU
                yield SuspendedForInputEvent(
                    question=tool_call.args["question"],
                    options=tool_call.args["options"],
                )
                return  # Run endet hier – kein weiterer LLM-Call
```

### Neues Event: `SuspendedForInputEvent`

```python
class SuspendedForInputEvent(AgentEvent):
    kind: Literal["onboarding_question"] = "onboarding_question"
    question: str
    options: list[str]
    question_id: UUID       # aus der DB, für die Antwort-Route
```

---

## 6. Statische Abschlussfrage: "Welche Playlists soll ich noch berücksichtigen?"

Diese Frage ist **nicht LLM-gesteuert**. Nachdem der Agent seine dynamischen Fragen abgeschlossen hat und in die BUILD-Phase übergeht, hängt das **Backend diese Frage automatisch an** – sie ergibt sich aus der Domain, nicht aus einem Tool-Call.

### Mechanismus: Domain-seitig angehängt

Wenn `Session.advance_to_building_phase()` aufgerufen wird, setzt das Backend **automatisch** ein `SuspendedForInputEvent(kind="playlist_context")` als letzten Event des Onboardings. Kein `request_playlist_context`-Tool, keine LLM-Entscheidung.

```python
# Im Backend, nach advance_to_building_phase():
yield SuspendedForInputEvent(kind="playlist_context")
# Frontend zeigt immer: "Welche Playlists soll ich noch berücksichtigen?"
```

Die Antwort landet wie bisher über den bestehenden `playlist_references`/`artist_references`-Mechanismus in der Session.

```python
class SuspendedForInputEvent(AgentEvent):
    kind: Literal["onboarding_question", "playlist_context"]
    question: str | None = None    # nur bei kind="onboarding_question"
    options: list[str] = []        # nur bei kind="onboarding_question"
    question_id: UUID | None = None
```

---

## 7. Nudge als UserMessage (kein System-Prompt)

Der Nudge wird **nicht** im System-Prompt platziert, sondern als **erste UserMessage** in die Konversation injiziert – direkt vor der eigentlichen Nachricht des Users. `MessageManager` hängt ihn einmalig an (nur wenn `phase=ONBOARDING` und noch keine Fragen gestellt wurden).

```
[UserMessage – Nudge]
Du sammelst jetzt Kontext für eine Playlist. Stelle 3–5 semantisch passende
Klärungsfragen basierend auf der Anfrage des Users. Themen-Orientierung
(NICHT hartcodiert – wähle was relevant ist):
- Für wen / zu welchem Anlass?
- Welche Jahrzehnte / Eras?
- Wie breit oder fokussiert soll das Spektrum sein?
- Stimmung / Vibe?
- Besondere Wünsche?

Rufe für jede Frage EINMAL `ask_onboarding_question` auf.
Du wirst nach jedem Aufruf pausieren – das ist gewollt.
Nachdem alle Fragen beantwortet sind, rufe `advance_to_build` auf.

[UserMessage – eigentliche Anfrage]
"Erstelle mir eine Playlist für..."
```

Der Nudge ist ein **statischer String aus einer Markdown-Datei** (`agent/messages/prompts/onboarding_nudge.md`), kein dynamisch generierter Prompt.

---

## 8. Backend-Resumption-Flow (Event-Propagation)

```
User sendet erste Nachricht
    → Agent(phase=ONBOARDING) startet
    → LLM ruft ask_onboarding_question({...}) auf
    → ActionResult(suspend=True) → SuspendedForInputEvent → SSE an Frontend
    → Agent-Run endet (Frage + Tool-Call-History in DB gespeichert)

Frontend zeigt Frage + Optionen
User antwortet
    → POST /sessions/{id}/onboarding-answer {question_id, answer}
    → Backend speichert Antwort (answer_onboarding_question)
    → Backend triggert neuen Agent-Run (gleiche Session)

Neuer Run:
    → MessageManager injiziert beantwortete Fragen als Kontext-Block
    → LLM sieht: Tool-Call-History + beantworteten Q&A-Context
    → LLM ruft ask_onboarding_question wieder auf (nächste Frage)
    → ... Schleife bis alle dynamischen Fragen gestellt sind

Nach letzter dynamischer Frage:
    → LLM ruft advance_to_build() auf
    → Backend: Session.advance_to_building_phase()
    → Backend sendet automatisch SuspendedForInputEvent(kind="playlist_context")
    → Frontend zeigt statisch: "Welche Playlists soll ich noch berücksichtigen?"
    → User wählt Playlists → POST /sessions/{id}/playlist-references (bestehender Mechanismus)
    → Backend speichert playlist_references
    → Phase ist bereits BUILD – nächster Agent-Run startet normal in BUILD
```

---

## 9. Implementierungs-Checkliste

### Datenbank
- [ ] `SessionOnboardingQuestionModel` hinzufügen (`backend/infrastructure/database/orm.py`)
- [ ] Alembic-Migration erstellen

### Domain
- [ ] `OnboardingQuestion` Entity (`backend/features/session/domain/entities/`)
- [ ] `Session` Aggregate: `add_onboarding_question`, `answer_onboarding_questions`, `get_answered_onboarding_context`
- [ ] Session-Mapper erweitern (ORM ↔ Domain)

### Agent
- [ ] `ActionType.INTERACT` zu `ActionType` hinzufügen (`agent/tools/views.py`)
- [ ] `suspend: bool` auf `ActionResult` (`agent/tools/views.py`)
- [ ] `suspends_for_input` Flag auf `Tool` (`agent/tools/views.py`)
- [ ] `SuspendedForInputEvent` (`agent/events.py`)
- [ ] `_run_loop` in `agent.py` – suspend-Check nach Tool-Result
- [ ] `AskOnboardingQuestionParams` + Tool-Funktion (`agent/tools/tools.py`)
- [ ] Onboarding-Nudge als UserMessage (`agent/messages/prompts/onboarding_nudge.md`)
- [ ] `MessageManager`: Onboarding-Kontext-Injektion

### Backend
- [ ] `POST /sessions/{id}/onboarding-answer` Endpoint
- [ ] Neuen Agent-Run nach Antwort triggern (bestehende `run`-Logik nutzen)

### Frontend
- [ ] `SuspendedForInputEvent(kind="onboarding_question")` rendern: Frage + Optionen-Buttons + Freitext-Escape
- [ ] `SuspendedForInputEvent(kind="playlist_context")` rendern: statische Playlist-Picker-Komponente ("Welche Playlists soll ich noch berücksichtigen?")
- [ ] Antwort-Submit: `POST /sessions/{id}/onboarding-answer` mit `{question_id, answer}`
- [ ] Playlist-Submit: bestehender `POST /sessions/{id}/playlist-references`-Flow
- [ ] Zustand: während Frage offen ist, Input-Feld + Chat deaktivieren (User muss erst antworten)

---

## 10. Offene Entscheidungen

| # | Frage | Empfehlung |
|---|-------|------------|
| 1 | Freitext-Option immer dabei? | Ja – jede Frage sollte "Sonstiges…"-Escape haben |
| 2 | Idempotenz bei Crash | `is_answered` prüfen im Tool – bereits gestellte Fragen nicht doppeln |
| 3 | Wer triggert neuen Run nach Antwort? | Backend-Route triggert direkt (kein expliziter Frontend-Re-Connect nötig) |
| 4 | Playlist-Frage: wann genau `SuspendedForInputEvent(kind="playlist_context")` senden? | Direkt nach `advance_to_building_phase()` – kein extra Tool, keine LLM-Entscheidung |
| 5 | Wie viele dynamische Fragen? | LLM entscheidet (3–5) via Nudge – nicht hardcoded |

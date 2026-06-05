# Onboarding-Fragen als First-Class-Artefakt (Backend)

## Ziel

Onboarding-Fragen sollen **nicht mehr als Tool-Calls** in der Session
gespeichert werden, sondern ausschließlich als `OnboardingQuestion`-Entities –
und jede Frage soll **einzeln, iterativ** über den Stream in die UI fließen
(wie das Claude-Streaming). Reiner Backend-Scope; Frontend folgt später.

## Kernidee

> Eine Onboarding-Frage ist ein **eigenständiges Domain-Artefakt**, kein
> Tool-Call. Der Tool-Call bleibt ein privates Detail der LLM-Konversation des
> Agents (`MessageManager`). Die Backend-`Session` sieht nur `OnboardingQuestion`s,
> und jede Frage wird als eigenes Stream-Event mit Reihenfolge-Metadaten gepusht.

Identität und Reihenfolge (`id`, `sequence_number`) werden an der **Domain-Grenze**
vergeben (`Session.add_onboarding_question` liefert sie zurück). Das Agent-Event
bleibt dadurch minimal, die Domain bleibt Source of Truth für Reihenfolge.

## Ist-Zustand (Problem)

Eine Frage läuft heute durch **zwei parallele Kanäle**:

1. **Tool-Call-Kanal:** `ToolCallEvent`/`ToolResultEvent` →
   `SessionRunnerToolCallStarted/Completed` → `session.add_tool_call()` →
   `ToolCallSequence` → SSE `tool_call.sequence_added`.
2. **Frage-Kanal:** `QuestionAskedEvent`/`SuspendedForUserInputEvent` →
   `SessionRunnerQuestionAsked/SuspendedForInput` → `session.add_onboarding_question()`.

`Session._reconstruct_onboarding_history()` entfernt danach die Tool-Call-Entries
wieder (`_is_onboarding_tool_call_sequence`). Diese Bereinigung existiert nur, um
Kanal #1 rückgängig zu machen — der eigentliche Hack.

Zwei Folgeprobleme:
- **Doppelte Speicherung** jeder Frage (ToolCallSequence + OnboardingQuestion).
- **Kein iteratives Streaming:** `_handle_question_asked`
  (`application/conversation_service.py`) ruft `add_onboarding_question` auf und
  gibt `()` zurück — **Zwischenfragen erzeugen kein SSE-Event**. Nur die letzte
  Frage streamt (über `SessionSuspendedForInput`).

## Soll-Zustand

- Onboarding-Fragen laufen **nur** über den Frage-Kanal.
- Der Agent emittiert für die Frage-Tools **keine** `ToolCallEvent`/`ToolResultEvent`
  mehr (die LLM-History in `MessageManager` behält Tool-Call + Result, damit die
  LLM-Konversation valide bleibt).
- Jede Frage – auch Zwischenfragen – wird als dediziertes Stream-Event gepusht.
- Suspendierung wird als **orthogonales Kontroll-Signal** behandelt, getrennt vom
  Fragen-Payload (eine Frage ist immer gleich geformt; "Run wartet jetzt" ist ein
  separates Signal).
- `_reconstruct_onboarding_history` vereinfacht sich auf das **Bauen der
  Zusammenfassung** für die Build-Phase (kein Strippen mehr).

## Metadaten-Modell (für iteratives Rendern)

Pro Frage im Stream:

| Feld | Quelle | Zweck in der UI |
|---|---|---|
| `question_id` | Domain (`OnboardingQuestion.id`) | Stabile Identität, Antwort-Zuordnung |
| `sequence_number` | Domain (`add_onboarding_question`) | Geordnetes, schrittweises Einblenden |
| `question` | Agent | Fragetext |
| `options` | Agent | Auswahlmöglichkeiten |
| `selection_mode` | Agent | single/multi-select Rendering |
| `is_last_question` | Agent | UI weiß: Sequenz ist komplett, jetzt warten |

`total_questions` ist während des Streamings nicht bekannt (das LLM emittiert
konsekutive Tool-Calls; die Gesamtzahl steht erst am Turn-Ende fest). Die UI nutzt
`is_last_question` als Abschluss-Signal und blendet bis dahin progressiv ein.
`sequence_number` genügt für die geordnete Darstellung.

## Architektur-Entscheidung: separate Collection beibehalten

`Session._onboarding_questions` bleibt eine **eigene Collection** parallel zu
`_entries` (Option A), statt `OnboardingQuestion` zu einem `SessionEntry` zu machen
(Option B).

- **Option A (gewählt):** Minimaler Eingriff, Entity hat `sequence_number` bereits,
  Antwort-Logik ist schon um die Collection herum gebaut, Entry-/History-Maschinerie
  bleibt stabil. Das iterative Streaming hängt am **Event**, nicht an der
  Entry-Zugehörigkeit – also voll erreichbar.
- **Option B (später möglich):** Fragen als Entries im einen geordneten Transcript.
  Eleganter als Langzeitmodell, aber größerer Refactor (Antwort-Lookup,
  `advance_to_building_phase`, `open_onboarding_questions`). Als Folgeschritt notiert.

## Umsetzung pro Schicht

### 1. Agent (`agent/src/agent/agent.py`)

In `_handle_tool_call`: Diskriminierung **result-getrieben** über
`result.input_request is not None`. Für Frage-Tools **keine**
`ToolCallEvent`/`ToolResultEvent` yielden; `self._messages.add_tool_result(...)`
bleibt (LLM-History valide). Nur das Frage-Event yielden.

Konsequenz: `ToolCallEvent` wird heute **vor** `execute` emittiert (Statusanzeige).
Da `input_request` erst nach `execute` bekannt ist, muss `ToolCallEvent` **nach**
`execute` wandern (kleine Reihenfolgeänderung). Damit wird die Statusanzeige für
normale Tools erst nach Ausführung gepusht – akzeptabel, da execute() für die
Build-Tools ohnehin schnell zurückkommt und die Statusanzeige primär das Ergebnis
einleitet. Falls die Vorab-Statusanzeige erhalten bleiben soll, kann `status_label`
weiterhin vor `execute` über ein separates Status-Event laufen; der `ToolCallEvent`
(der die Persistenz als ToolCallSequence auslöst) bleibt aber nach `execute`.

```python
async def _handle_tool_call(self, call):
    args = self._tools.parse_args(call)
    tool = self._tools.get(call.function.name, phase=self._phase)

    result = await self._tools.execute(call.function.name, args, phase=self._phase)
    content = result.to_content()
    is_question = result.input_request is not None

    if not is_question:
        yield ToolCallEvent(...)
        yield ToolResultEvent(...)

    for update in self._playlist_store.drain_playlist_draft_updates():
        yield WorkspaceUpdatedEvent(...)

    self._messages.add_tool_result(tool_call_id=call.id, content=content)

    request = result.input_request
    if request is not None:
        ... QuestionAskedEvent / SuspendedForUserInputEvent
```

### 2. Infrastructure-Mapper (`infrastructure/agent_event_mapper.py`)

Unverändert in der Struktur – `QuestionAskedEvent`/`SuspendedForUserInputEvent`
werden weiterhin gemappt. Da der Agent für Fragen keine `ToolCallEvent` mehr
schickt, entstehen automatisch keine `SessionRunnerToolCallStarted` für Fragen.

### 3. Application (`application/conversation_service.py` + `events.py`)

- Neues App-Event `SessionOnboardingQuestionAdded(question: OnboardingQuestion)`
  in `application/events.py`, in die `SessionEvent`-Union aufnehmen.
- `_handle_question_asked`: zuerst `_finish_current_assistant_message(...)`
  (Intro-Bubble schließen, bevor Fragen streamen – macht heute nur
  `_handle_suspended_for_input`), dann `add_onboarding_question(...)`, dann
  `SessionOnboardingQuestionAdded(question=...)` emittieren (statt `()`).
- `_handle_suspended_for_input`: Frage als `SessionOnboardingQuestionAdded`
  emittieren **plus** ein schlankes `SessionSuspendedForInput(kind=ONBOARDING_QUESTION)`
  als reines Kontroll-/Pause-Signal (ohne Fragen-Payload zu duplizieren).
  `question_id` kann zur Kompatibilität noch mitgegeben werden.

### 4. Domain (`domain/session.py`)

- `_reconstruct_onboarding_history`: Strip-Logik entfernen
  (`_is_onboarding_tool_call_sequence` + Filter über `_entries`). Nur noch die
  Q&A-Zusammenfassung (`UserMessage`/`AssistantMessage`) für die Build-Phase
  anhängen. `_is_onboarding_tool_call_sequence` wird damit toter Code → löschen.
- Sicherstellen, dass während Onboarding keine `ToolCallSequence` mehr für Fragen
  entsteht (folgt automatisch aus Schicht 1/3).

### 5. Presentation / SSE (`presentation/sse/events.py` + `mappers.py`)

- Neuer Event-Typ `OnboardingQuestionAddedEvent`
  (`type = "onboarding.question_added"`) mit Feldern:
  `question_id, sequence_number, question, options, selection_mode, is_last_question`.
  In `SessionEventType` und die `ServerEvent`-Union aufnehmen.
- `to_server_event`: `SessionOnboardingQuestionAdded` → `OnboardingQuestionAddedEvent`.
- `SuspendedForInputEvent` bleibt, trägt für Onboarding aber keinen Fragen-Payload
  mehr (Frage kommt über `onboarding.question_added`). Für `playlist_context`
  unverändert.

## Tests

- Agent: Frage-Tool erzeugt **keine** `ToolCallEvent`/`ToolResultEvent`, nur
  `QuestionAskedEvent`/`SuspendedForUserInputEvent`; LLM-History enthält weiterhin
  Tool-Call + Result.
- Application: jede Frage (inkl. Zwischenfragen) erzeugt genau ein
  `SessionOnboardingQuestionAdded`; letzte Frage zusätzlich `SessionSuspendedForInput`.
  Keine `SessionToolCallSequenceAdded` während Onboarding.
- Domain: nach Beantwortung der letzten Frage enthält `_entries` keine
  Onboarding-`ToolCallSequence` (gab es nie) und die Q&A-Zusammenfassung ist vorhanden.
- Bestehende Tests im Onboarding-Pfad anpassen (Doppelspeicherung entfällt).

## Offene Punkte / später

- Option B (OnboardingQuestion als `SessionEntry`) für ein einheitliches
  Transcript.
- `total_questions` optional vom LLM mitgeben, falls die UI eine feste
  Fortschrittsanzeige ("Frage 2 von 4") will.

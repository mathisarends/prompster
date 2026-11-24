import asyncio
from collections.abc import AsyncIterator, Callable, Sequence
from typing import Any

import pytest
from agent.activity import ActionType, ToolCallAnnouncedEvent
from agent.agent import Agent, Phase
from agent.conversation import AgentCheckpoint, AgentCommit, AssistantRepliedEvent
from agent.deck import (
    Deck,
    DeckCreatedEvent,
    DeckTrack,
    DeckTracksRemovedEvent,
)
from agent.events import AgentEvent
from agent.onboarding import QuestionAskedEvent
from agent.research import TracksFoundEvent
from harnessed import SessionStatus
from harnessed.events import (
    CompactionAppliedEvent,
    CompactionFinishedEvent,
    CompactionStartedEvent,
    SessionStatusChangedEvent,
    TextDeltaEvent,
    ToolCallFinishedEvent,
)
from harnessed.events.completion import TurnResultEvent
from harnessed.models import StopReason
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.messages import ModelRequest, UserPromptPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from tests.agent.conftest import TAKE_ON_ME, FakeSpotify, ScriptedLlm

_SEARCH = {"call-search": ("search_tracks", {"query": "a-ha"})}
_ADD = {
    "call-add": (
        "add_deck_tracks",
        {"uris": [TAKE_ON_ME.uri], "status": "Baue das 80er-Deck"},
    )
}


def _build_agent(llm: Any, **options: Any) -> Agent:
    options.setdefault("spotify", FakeSpotify(TAKE_ON_ME))
    return Agent(llm.model, phase=Phase.BUILD, **options)


async def _run(agent: Agent, text: str = "Los") -> list[AgentEvent]:
    async with agent:
        return [event async for event in agent.stream(text)]


def _of[E](events: Sequence[object], kind: type[E]) -> list[E]:
    return [event for event in events if isinstance(event, kind)]


def _index(events: Sequence[object], kind: type) -> int:
    return next(i for i, event in enumerate(events) if isinstance(event, kind))


def _result(events: Sequence[object]) -> TurnResultEvent[Any]:
    result = events[-1]
    assert isinstance(result, TurnResultEvent)
    return result


def _user_prompts(request: list[Any]) -> list[str]:
    return [
        str(part.content)
        for message in request
        if isinstance(message, ModelRequest)
        for part in message.parts
        if isinstance(part, UserPromptPart)
    ]


@pytest.mark.asyncio
async def test_stream_yields_deltas_then_the_reply_then_the_result(
    scripted_llm: Callable[..., Any],
) -> None:
    llm = scripted_llm(("Hallo", " Welt"))

    events = await _run(Agent(llm.model), "Sag hallo")

    deltas = [event.text for event in _of(events, TextDeltaEvent) if event.text]
    reply = _of(events, AssistantRepliedEvent)
    assert deltas == ["Hallo", " Welt"]
    assert [(r.text, r.final) for r in reply] == [("Hallo Welt", True)]
    assert _result(events).result.stop_reason is StopReason.END


@pytest.mark.asyncio
async def test_found_tracks_become_addable_and_deck_changes_follow_the_call(
    scripted_llm: Callable[..., Any],
) -> None:
    llm = scripted_llm(_SEARCH, _ADD, "Der Entwurf ist bereit.")
    agent = _build_agent(llm)

    events = await _run(agent, "Bau mir ein Deck")

    found = _of(events, TracksFoundEvent)
    announced = {e.call.id: e for e in _of(events, ToolCallAnnouncedEvent)}
    finished = {e.call.id: e for e in _of(events, ToolCallFinishedEvent)}
    created = _of(events, DeckCreatedEvent)
    assert found[0].tracks == (TAKE_ON_ME,)
    assert announced["call-add"].action_type is ActionType.ADD_DECK_TRACKS
    assert announced["call-add"].status_label == "Baue das 80er-Deck"
    assert announced["call-search"].status_label == "Suche Tracks: a-ha"
    assert finished["call-add"].result.text == (
        'Added 1 track(s) to Hitster deck "Deck" (1 total).'
    )
    assert _index(events, DeckCreatedEvent) < events.index(finished["call-add"])
    assert created[0].deck.tracks[0].title == "Take On Me"
    assert agent.deck == created[0].deck


@pytest.mark.asyncio
async def test_ui_labels_never_reach_the_tool(
    scripted_llm: Callable[..., Any],
) -> None:
    add = {
        "call-add": (
            "add_deck_tracks",
            {
                "uris": [TAKE_ON_ME.uri],
                "status": "Lege Tracks ab",
                "sequence_label": "Deck bauen",
            },
        )
    }
    llm = scripted_llm(_SEARCH, add, "Fertig.")

    events = await _run(_build_agent(llm))

    finished = {e.call.id: e for e in _of(events, ToolCallFinishedEvent)}
    announced = {e.call.id: e for e in _of(events, ToolCallAnnouncedEvent)}
    assert finished["call-add"].result.text.startswith("Added 1 track(s)")
    assert announced["call-add"].batch_label == "Deck bauen"


@pytest.mark.asyncio
async def test_unknown_uris_go_back_to_the_model(
    scripted_llm: Callable[..., Any],
) -> None:
    llm = scripted_llm(_ADD, "Ich suche zuerst.")
    agent = _build_agent(llm)

    events = await _run(agent)

    finished = _of(events, ToolCallFinishedEvent)[0]
    assert "Unknown Spotify track URI" in finished.result.text
    assert agent.deck is None
    assert len(llm.requests) == 2


@pytest.mark.asyncio
async def test_every_request_ends_with_the_live_deck_state(
    scripted_llm: Callable[..., Any],
) -> None:
    llm = scripted_llm(_SEARCH, _ADD, "Fertig.")

    await _run(_build_agent(llm))

    assert 'track_count="0"' in _user_prompts(llm.requests[1])[-1]
    assert 'track_count="1"' in _user_prompts(llm.requests[2])[-1]


@pytest.mark.asyncio
async def test_final_reply_settles_duplicate_deck_tracks_first(
    scripted_llm: Callable[..., Any],
) -> None:
    first = DeckTrack(id="t1", title="Take On Me", artist="a-ha", spotify_uri="u:1")
    duplicate = DeckTrack(id="t2", title="Take On Me", artist="a-ha", spotify_uri="u:1")
    other = DeckTrack(id="t3", title="Billie Jean", artist="Michael Jackson")
    deck = Deck(id="d1", name="80er Party", tracks=(first, duplicate, other))
    llm = scripted_llm("Der Entwurf ist bereit.")
    agent = _build_agent(llm, deck=deck)

    events = await _run(agent, "Fertig?")

    removed = _of(events, DeckTracksRemovedEvent)
    assert removed[0].track_ids == ("t2",)
    assert _index(events, DeckTracksRemovedEvent) < _index(
        events, AssistantRepliedEvent
    )
    assert agent.deck is not None
    assert [track.id for track in agent.deck.tracks] == ["t1", "t3"]


@pytest.mark.asyncio
async def test_phases_offer_their_own_tools(scripted_llm: Callable[..., Any]) -> None:
    onboarding = scripted_llm("ok")
    build = scripted_llm("ok")

    await _run(Agent(onboarding.model), "Hallo")
    await _run(_build_agent(build), "Bau mir ein Deck")

    assert onboarding.tool_names[0] == {"ask_onboarding_question"}
    assert build.tool_names[0] == {
        "search_tracks",
        "search_playlists",
        "get_spotify_playlist_tracks",
        "add_deck_tracks",
        "remove_deck_tracks",
        "replace_deck_tracks",
        "review_deck",
    }


@pytest.mark.asyncio
async def test_only_tools_without_derived_labels_ask_for_a_status(
    scripted_llm: Callable[..., Any],
) -> None:
    llm = scripted_llm("ok")

    await _run(_build_agent(llm))

    schemas = {
        tool.name: tool.parameters_json_schema["properties"]
        for tool in llm.infos[0].function_tools
    }
    assert "status" not in schemas["search_tracks"]
    assert "sequence_label" in schemas["search_tracks"]
    assert "status" in schemas["add_deck_tracks"]


@pytest.mark.asyncio
async def test_tool_schemas_come_from_the_tool_signatures(
    scripted_llm: Callable[..., Any],
) -> None:
    onboarding = scripted_llm("ok")
    build = scripted_llm("ok")

    await _run(Agent(onboarding.model), "Hallo")
    await _run(_build_agent(build))

    tools = {
        tool.name: tool
        for llm in (onboarding, build)
        for tool in llm.infos[0].function_tools
    }
    add = tools["add_deck_tracks"].parameters_json_schema
    question = tools["ask_onboarding_question"].parameters_json_schema
    assert tools["add_deck_tracks"].description.startswith("Add tracks")
    assert add["properties"]["uris"]["minItems"] == 1
    assert add["properties"]["uris"]["items"]["pattern"] == "^spotify:track:"
    assert question["properties"]["options"]["minItems"] == 2
    assert question["properties"]["options"]["maxItems"] == 4
    assert {"hint", "recommended_option"}.isdisjoint(question["required"])


@pytest.mark.asyncio
@pytest.mark.parametrize(("is_last", "requests"), [(True, 1), (False, 2)])
async def test_only_the_last_onboarding_question_ends_the_turn(
    scripted_llm: Callable[..., Any],
    is_last: bool,
    requests: int,
) -> None:
    question = {
        "question": "Fuer wen ist die Playlist?",
        "hint": "Die Zielgruppe hilft beim Schwierigkeitsgrad.",
        "options": ["Freunde", "Familie", "Kolleg:innen"],
        "is_last_question": is_last,
    }
    llm = scripted_llm({"call-1": ("ask_onboarding_question", question)}, "weiter")

    events = await _run(Agent(llm.model), "Start")

    asked = _of(events, QuestionAskedEvent)[0]
    assert asked.options == ("Freunde", "Familie", "Kolleg:innen")
    assert asked.is_last_question is is_last
    assert not _of(events, ToolCallAnnouncedEvent)
    assert len(llm.requests) == requests


@pytest.mark.asyncio
async def test_commits_reopen_the_agent_with_its_history_and_catalog(
    scripted_llm: Callable[..., Any],
) -> None:
    commits: list[AgentCommit] = []

    async def store(commit: AgentCommit) -> None:
        commits.append(commit)

    first = scripted_llm(_SEARCH, "Gefunden.")
    await _run(_build_agent(first, on_commit=store, session_id="s1"), "Suche a-ha")
    second = scripted_llm(_ADD, "Hinzugefuegt.")
    reopened = _build_agent(
        second, checkpoint=_checkpoint(commits), session_id="s1", spotify=FakeSpotify()
    )

    events = await _run(reopened, "Nimm Take On Me")

    assert _user_prompts(second.requests[0])[0] == "Suche a-ha"
    assert _of(events, DeckCreatedEvent)
    assert any(commit.state is None for commit in commits)


@pytest.mark.asyncio
async def test_switching_models_continues_the_conversation(
    scripted_llm: Callable[..., Any],
) -> None:
    commits: list[AgentCommit] = []

    async def store(commit: AgentCommit) -> None:
        commits.append(commit)

    await _run(Agent(scripted_llm("Hi").model, on_commit=store, session_id="s1"))
    other = scripted_llm("Hallo again", model_name="other")

    events = await _run(
        Agent(other.model, checkpoint=_checkpoint(commits), session_id="s1"), "Weiter"
    )

    assert _result(events).result.text == "Hallo again"


@pytest.mark.asyncio
async def test_pause_holds_the_turn_until_resume() -> None:
    gate = asyncio.Event()
    llm = ScriptedLlm([_SEARCH, "Fertig."])
    agent = _build_agent(llm, spotify=FakeSpotify(TAKE_ON_ME, gate=gate))
    statuses: list[SessionStatus] = []

    async with agent:
        async for event in agent.stream("Los"):
            if isinstance(event, ToolCallAnnouncedEvent):
                pausing = asyncio.create_task(agent.pause())
                gate.set()
                await asyncio.wait_for(pausing, timeout=5)
            if isinstance(event, SessionStatusChangedEvent):
                statuses.append(event.status)
                if event.status is SessionStatus.PAUSED:
                    assert len(llm.requests) == 1
                    await agent.resume()
            last = event

    assert SessionStatus.PAUSED in statuses
    assert statuses.index(SessionStatus.PAUSED) < len(statuses) - 1
    assert isinstance(last, TurnResultEvent)
    assert last.result.text == "Fertig."


@pytest.mark.asyncio
async def test_abort_ends_a_running_turn() -> None:
    started = asyncio.Event()

    async def hang(_messages: list[Any], _info: AgentInfo) -> AsyncIterator[str]:
        yield "Teil"
        started.set()
        await asyncio.Event().wait()

    agent = Agent(FunctionModel(stream_function=hang, model_name="hanging"))

    async def abort_once_started() -> None:
        await started.wait()
        await agent.abort()

    async with agent:
        aborting = asyncio.create_task(abort_once_started())
        events = await asyncio.wait_for(_collect(agent), timeout=5)
        await asyncio.wait_for(aborting, timeout=5)

    assert _result(events).result.stop_reason is StopReason.ABORTED


@pytest.mark.asyncio
async def test_paused_checkpoint_reopens_ready_for_the_next_message() -> None:
    commits: list[AgentCommit] = []

    async def store(commit: AgentCommit) -> None:
        commits.append(commit)

    gate = asyncio.Event()
    paused = _build_agent(
        ScriptedLlm([_SEARCH, "nie"]),
        spotify=FakeSpotify(TAKE_ON_ME, gate=gate),
        on_commit=store,
        session_id="s1",
    )
    async with paused:
        async for event in paused.stream("Los"):
            if isinstance(event, ToolCallAnnouncedEvent):
                pausing = asyncio.create_task(paused.pause())
                gate.set()
                await asyncio.wait_for(pausing, timeout=5)
            if (
                isinstance(event, SessionStatusChangedEvent)
                and event.status is SessionStatus.PAUSED
            ):
                break
    reopened = _build_agent(
        ScriptedLlm(["Neu gestartet."]),
        checkpoint=_checkpoint(commits),
        session_id="s1",
    )

    events = await _run(reopened, "Nochmal")

    assert _result(events).result.text == "Neu gestartet."


@pytest.mark.asyncio
async def test_context_overflow_compacts_and_retries(
    scripted_llm: Callable[..., Any],
) -> None:
    commits: list[AgentCommit] = []

    async def store(commit: AgentCommit) -> None:
        commits.append(commit)

    searches = [
        {f"call-{index}": ("search_tracks", {"query": f"q{index}"})}
        for index in range(6)
    ]
    await _run(
        _build_agent(
            scripted_llm(*searches, "Gesucht."), on_commit=store, session_id="s1"
        )
    )
    overflow = ModelHTTPError(
        status_code=400,
        model_name="scripted",
        body={"code": "context_length_exceeded", "message": "too long"},
        provider_error_code="context_length_exceeded",
    )
    llm = scripted_llm(overflow, "Zusammenfassung", "Weiter gehts")

    events = await _run(
        _build_agent(llm, checkpoint=_checkpoint(commits), session_id="s1"), "Weiter"
    )

    started = _of(events, CompactionStartedEvent)
    applied = _of(events, CompactionAppliedEvent)
    finished = _of(events, CompactionFinishedEvent)
    assert started and applied and finished
    assert applied[0].after_tokens < applied[0].before_tokens
    assert _result(events).result.text == "Weiter gehts"


async def _collect(agent: Agent) -> list[AgentEvent]:
    return [event async for event in agent.stream("Los")]


def _checkpoint(commits: Sequence[AgentCommit]) -> AgentCheckpoint:
    state = next(c.state for c in reversed(commits) if c.state is not None)
    return AgentCheckpoint(state=state, execution=commits[-1].execution)


@pytest.mark.asyncio
async def test_onboarding_checkpoint_continues_in_the_build_phase(
    scripted_llm: Callable[..., Any],
) -> None:
    commits: list[AgentCommit] = []

    async def store(commit: AgentCommit) -> None:
        commits.append(commit)

    question = {
        "question": "Fuer wen?",
        "options": ["Freunde", "Familie"],
        "is_last_question": True,
    }
    onboarding = scripted_llm({"call-q": ("ask_onboarding_question", question)})
    await _run(Agent(onboarding.model, on_commit=store, session_id="s1"), "Start")
    build = scripted_llm("Los gehts.")

    events = await _run(
        _build_agent(build, checkpoint=_checkpoint(commits), session_id="s1"),
        "Antwort: Freunde",
    )

    assert _result(events).result.text == "Los gehts."
    assert _user_prompts(build.requests[0])[0] == "Start"

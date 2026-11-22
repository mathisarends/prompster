import asyncio
from collections.abc import AsyncIterator, Callable
from typing import Any

import pytest
from agent.agent import Agent
from agent.deck import DeckDraft, DeckDraftTrack, DeckDraftTracksRemoved, DeckStore
from agent.events import (
    AssistantMessageChunkEvent,
    AssistantMessageEvent,
    ContextCompactedEvent,
    DeckUpdatedEvent,
    QuestionAskedEvent,
    RunCompletedEvent,
    SuspendedForUserInputEvent,
    ToolCallEvent,
    ToolResultEvent,
)
from agent.tools.views import ActionType
from agent.views import Phase
from harnessed.models import AssistantMessage, ToolCall, ToolMessage, UserMessage
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.messages import ModelRequest, UserPromptPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

_TAKE_ON_ME_URI = "spotify:track:2WfaOiMkCvy7F5fcp2zZ8L"


def _track(
    title: str = "Take On Me",
    artist: str = "a-ha",
    uri: str = _TAKE_ON_ME_URI,
    year: int = 1985,
) -> DeckDraftTrack:
    return DeckDraftTrack(title=title, artist=artist, year=year, spotify_uri=uri)


def _question(*, is_last: bool) -> dict[str, Any]:
    return {
        "question": "Fuer wen ist die Playlist?",
        "hint": "Die Zielgruppe hilft beim Schwierigkeitsgrad.",
        "options": ["Freunde", "Familie", "Kolleg:innen"],
        "is_last_question": is_last,
    }


def _last_user_text(request: list[Any]) -> str:
    message = request[-1]
    assert isinstance(message, ModelRequest)
    parts = [part for part in message.parts if isinstance(part, UserPromptPart)]
    return str(parts[-1].content)


async def _collect(agent: Agent, message: str | None = "Los") -> list[Any]:
    return [event async for event in agent.stream(message)]


@pytest.mark.asyncio
async def test_stream_emits_chunks_before_the_completed_message(
    scripted_llm: Callable[..., Any],
) -> None:
    llm = scripted_llm(("Hallo", " Welt"))

    events = await _collect(Agent(llm=llm.model), "Sag hallo")

    chunks = [e.chunk for e in events if isinstance(e, AssistantMessageChunkEvent)]
    completed = next(e for e in events if isinstance(e, AssistantMessageEvent))
    assert chunks == ["Hallo", " Welt"]
    assert completed.content == "Hallo Welt"
    assert isinstance(events[-1], RunCompletedEvent)
    assert events[-1].output == "Hallo Welt"


@pytest.mark.asyncio
async def test_context_length_error_compacts_and_retries(
    scripted_llm: Callable[..., Any],
) -> None:
    overflow = ModelHTTPError(
        status_code=400,
        model_name="scripted",
        body={"code": "context_length_exceeded", "message": "too long"},
        provider_error_code="context_length_exceeded",
    )
    llm = scripted_llm(overflow, "Zusammenfassung", "Weiter gehts")
    history: list[Any] = [UserMessage("Bau ein Deck")]
    for index in range(6):
        call = ToolCall("search_tracks", {"query": str(index)}, id=f"call-{index}")
        history.append(AssistantMessage("", (call,)))
        history.append(ToolMessage("x", tool_call_id=call.id))
    agent = Agent(llm=llm.model, history=history, phase=Phase.BUILD)

    events = await _collect(agent, "Mach weiter")

    compacted = next(e for e in events if isinstance(e, ContextCompactedEvent))
    completed = next(e for e in events if isinstance(e, AssistantMessageEvent))
    assert compacted.reason == "reactive"
    assert completed.content == "Weiter gehts"


@pytest.mark.asyncio
async def test_deck_update_follows_its_tool_result(
    scripted_llm: Callable[..., Any],
) -> None:
    store = DeckStore()
    store.cache_tracks([_track()])
    llm = scripted_llm(
        {
            "call-1": (
                "add_deck_tracks",
                {"tracks": [{"uri": _TAKE_ON_ME_URI}], "status": "Baue das 80er-Deck"},
            )
        },
        "Der Entwurf ist bereit.",
    )
    agent = Agent(llm=llm.model, deck_store=store, phase=Phase.BUILD)

    events = await _collect(agent, "Bau mir ein Deck")

    result_index = next(
        i for i, e in enumerate(events) if isinstance(e, ToolResultEvent)
    )
    update_index = next(
        i for i, e in enumerate(events) if isinstance(e, DeckUpdatedEvent)
    )
    tool_call = next(e for e in events if isinstance(e, ToolCallEvent))
    assert update_index == result_index + 1
    assert tool_call.action_type == ActionType.ADD_DECK_TRACKS
    assert tool_call.status_label == "Baue das 80er-Deck"
    assert events[result_index].result == (
        'Added 1 track(s) to Hitster deck "Deck" (1 total).'
    )
    assert events[update_index].deck_draft.tracks[0].title == "Take On Me"
    assert store.drain_deck_draft_updates() == []


@pytest.mark.asyncio
async def test_ui_labels_never_reach_the_tool_or_the_replayed_arguments(
    scripted_llm: Callable[..., Any],
) -> None:
    store = DeckStore()
    store.cache_tracks([_track()])
    llm = scripted_llm(
        {
            "call-1": (
                "add_deck_tracks",
                {
                    "tracks": [{"uri": _TAKE_ON_ME_URI}],
                    "status": "Lege Tracks ab",
                    "sequence_label": "Deck bauen",
                },
            )
        },
        "Fertig.",
    )
    agent = Agent(llm=llm.model, deck_store=store, phase=Phase.BUILD)

    events = await _collect(agent)

    result = next(e for e in events if isinstance(e, ToolResultEvent))
    assert result.result.startswith("Added 1 track(s)")


@pytest.mark.asyncio
async def test_every_request_ends_with_the_live_deck_state(
    scripted_llm: Callable[..., Any],
) -> None:
    store = DeckStore()
    store.cache_tracks([_track()])
    llm = scripted_llm(
        {"call-1": ("add_deck_tracks", {"tracks": [{"uri": _TAKE_ON_ME_URI}]})},
        "Fertig.",
    )
    agent = Agent(llm=llm.model, deck_store=store, phase=Phase.BUILD)

    await _collect(agent)

    assert 'track_count="0"' in _last_user_text(llm.requests[0])
    assert 'track_count="1"' in _last_user_text(llm.requests[1])


@pytest.mark.asyncio
async def test_completion_guardrail_removes_duplicate_deck_tracks(
    scripted_llm: Callable[..., Any],
) -> None:
    first = _track()
    duplicate = _track()
    other = _track("Billie Jean", "Michael Jackson", "spotify:track:billie", 1982)
    store = DeckStore(DeckDraft(name="80er Party", tracks=[first, duplicate, other]))
    llm = scripted_llm("Der Entwurf ist bereit.")
    agent = Agent(llm=llm.model, deck_store=store, phase=Phase.BUILD)

    events = await _collect(agent, "Fertig?")

    update_index = next(
        i for i, e in enumerate(events) if isinstance(e, DeckUpdatedEvent)
    )
    message_index = next(
        i for i, e in enumerate(events) if isinstance(e, AssistantMessageEvent)
    )
    assert update_index < message_index
    assert isinstance(events[update_index].update, DeckDraftTracksRemoved)
    assert events[update_index].update.track_ids == [duplicate.id]
    assert store.draft is not None
    assert [track.id for track in store.draft.tracks] == [first.id, other.id]


@pytest.mark.asyncio
async def test_onboarding_phase_offers_only_the_question_tool(
    scripted_llm: Callable[..., Any],
) -> None:
    llm = scripted_llm("ok")
    agent = Agent(llm=llm.model)

    await _collect(agent, "Hallo")

    assert agent.phase == Phase.ONBOARDING
    assert llm.tool_names[0] == {"ask_onboarding_question"}


@pytest.mark.asyncio
async def test_build_phase_offers_research_and_deck_tools(
    scripted_llm: Callable[..., Any],
) -> None:
    llm = scripted_llm("ok")

    await _collect(Agent(llm=llm.model, phase=Phase.BUILD), "Bau mir ein Deck")

    assert llm.tool_names[0] == {
        "search_tracks",
        "search_playlists",
        "get_spotify_playlist_tracks",
        "add_deck_tracks",
        "remove_deck_tracks",
        "replace_deck_tracks",
        "review_deck",
    }


@pytest.mark.asyncio
async def test_last_onboarding_question_suspends_the_run(
    scripted_llm: Callable[..., Any],
) -> None:
    llm = scripted_llm(
        {"call-1": ("ask_onboarding_question", _question(is_last=True))},
        "should-not-run",
    )

    events = await _collect(Agent(llm=llm.model), "Start")

    suspended = next(e for e in events if isinstance(e, SuspendedForUserInputEvent))
    assert suspended.options == ["Freunde", "Familie", "Kolleg:innen"]
    assert not any(isinstance(e, ToolCallEvent | ToolResultEvent) for e in events)
    assert not any(isinstance(e, RunCompletedEvent) for e in events)
    assert len(llm.requests) == 1


@pytest.mark.asyncio
async def test_earlier_onboarding_question_keeps_the_run_going(
    scripted_llm: Callable[..., Any],
) -> None:
    llm = scripted_llm(
        {"call-1": ("ask_onboarding_question", _question(is_last=False))},
        "done",
    )

    events = await _collect(Agent(llm=llm.model), "Start")

    question = next(e for e in events if isinstance(e, QuestionAskedEvent))
    assert question.hint == "Die Zielgruppe hilft beim Schwierigkeitsgrad."
    assert not any(isinstance(e, SuspendedForUserInputEvent) for e in events)
    assert len(llm.requests) == 2


@pytest.mark.asyncio
async def test_invalid_tool_arguments_go_back_to_the_model(
    scripted_llm: Callable[..., Any],
) -> None:
    llm = scripted_llm(
        {"call-1": ("add_deck_tracks", {"tracks": [{"uri": "spotify:album:nope"}]})},
        "Korrigiert.",
    )
    store = DeckStore()

    await _collect(Agent(llm=llm.model, deck_store=store, phase=Phase.BUILD))

    assert len(llm.requests) == 2
    assert store.draft is None


@pytest.mark.asyncio
async def test_only_tools_without_derived_labels_ask_for_a_status(
    scripted_llm: Callable[..., Any],
) -> None:
    llm = scripted_llm("ok")

    await _collect(Agent(llm=llm.model, phase=Phase.BUILD))

    schemas = {
        tool.name: tool.parameters_json_schema["properties"]
        for tool in llm.infos[0].function_tools
    }
    assert "status" not in schemas["search_tracks"]
    assert "sequence_label" in schemas["search_tracks"]
    assert "status" in schemas["add_deck_tracks"]


@pytest.mark.asyncio
async def test_trailing_user_message_is_the_run_input(
    scripted_llm: Callable[..., Any],
) -> None:
    llm = scripted_llm("Klar")
    history = [
        UserMessage("Erste Frage"),
        AssistantMessage("Antwort"),
        UserMessage("Zweite Frage"),
    ]

    await _collect_without_message(Agent(llm=llm.model, history=history))

    prompts = [
        part.content
        for message in llm.requests[0]
        if isinstance(message, ModelRequest)
        for part in message.parts
        if isinstance(part, UserPromptPart)
    ]
    assert prompts == ["Erste Frage", "Zweite Frage"]


@pytest.mark.asyncio
async def test_request_stop_ends_a_running_stream_without_completion() -> None:
    started = asyncio.Event()

    async def hang(_messages: list[Any], _info: AgentInfo) -> AsyncIterator[str]:
        yield "Teil"
        started.set()
        await asyncio.Event().wait()

    agent = Agent(llm=FunctionModel(stream_function=hang, model_name="hanging"))

    async def stop_once_started() -> None:
        await started.wait()
        agent.request_stop()

    stopper = asyncio.create_task(stop_once_started())
    events = await asyncio.wait_for(_collect(agent), timeout=5)
    await asyncio.wait_for(stopper, timeout=5)

    assert not any(isinstance(e, RunCompletedEvent) for e in events)


async def _collect_without_message(agent: Agent) -> list[Any]:
    return [event async for event in agent.stream()]

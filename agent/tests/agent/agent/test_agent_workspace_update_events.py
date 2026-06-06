import json
from dataclasses import dataclass
from typing import Any

from llmify import StreamEnd, StreamTextDelta, StreamToolCall
from llmify.messages import ToolCall
import pytest

from agent.agent import (
    Agent,
    AssistantMessageChunkEvent,
    AssistantMessageEvent,
    QuestionAskedEvent,
    ToolCallEvent,
    ToolResultEvent,
    SuspendedForUserInputEvent,
    DeckUpdatedEvent,
)
from agent.tools import ToolContext, Tools
from agent.tools.views import ActionType, Phase
from agent.deck import DeckStore, DeckDraftTrack


@dataclass
class _ChatResponse:
    completion: str | None
    tool_calls: list[ToolCall]
    chunks: list[str] | None = None


class _FakeLlm:
    def __init__(self, responses: list[_ChatResponse]) -> None:
        self._responses = responses
        self.tool_schema_batches: list[list[Any]] = []

    async def stream(self, messages: list[Any], tools: list[Any]):
        self.tool_schema_batches.append(tools)
        response = self._responses.pop(0)
        for chunk in response.chunks or []:
            yield StreamTextDelta(delta=chunk)
        for tool_call in response.tool_calls:
            yield StreamToolCall(tool_call=tool_call)
        yield StreamEnd(
            completion=response.completion or "",
            tool_calls=response.tool_calls,
        )


class TestAgentWorkspaceUpdateEvents:
    @pytest.mark.asyncio
    async def test_stream_emits_assistant_chunks_before_completed_message(self) -> None:
        llm = _FakeLlm(
            [
                _ChatResponse(
                    completion="Hallo Welt",
                    chunks=["Hallo", " Welt"],
                    tool_calls=[],
                )
            ]
        )
        agent = Agent(llm=llm)

        events = [event async for event in agent.stream("Sag hallo")]

        chunks = [
            event.chunk
            for event in events
            if isinstance(event, AssistantMessageChunkEvent)
        ]
        completed = next(
            event for event in events if isinstance(event, AssistantMessageEvent)
        )

        assert chunks == ["Hallo", " Welt"]
        assert completed.content == "Hallo Welt"

    @pytest.mark.asyncio
    async def test_stream_emits_deck_update_after_tool_result(self) -> None:
        store = DeckStore()
        store.cache_tracks(
            [
                DeckDraftTrack(
                    title="Take On Me",
                    artist="a-ha",
                    year=1985,
                    spotify_uri="spotify:track:2WfaOiMkCvy7F5fcp2zZ8L",
                    cover_url="https://i.scdn.co/image/take-on-me.jpg",
                )
            ]
        )
        tools = Tools(ToolContext(store))
        tool_args = {
            "status": "Baue das 80er-Deck",
            "tracks": [{"uri": "spotify:track:2WfaOiMkCvy7F5fcp2zZ8L"}],
        }
        llm = _FakeLlm(
            [
                _ChatResponse(
                    completion="",
                    tool_calls=[
                        ToolCall(
                            id="call-1",
                            function={
                                "name": "add_deck_tracks",
                                "arguments": json.dumps(tool_args),
                            },
                        )
                    ],
                ),
                _ChatResponse(completion="Der Entwurf ist bereit.", tool_calls=[]),
            ]
        )
        agent = Agent(llm=llm, tools=tools, phase=Phase.BUILD)

        events = [event async for event in agent.stream("Bau mir ein Deck")]

        tool_result_index = next(
            index
            for index, event in enumerate(events)
            if isinstance(event, ToolResultEvent)
        )
        tool_call = next(event for event in events if isinstance(event, ToolCallEvent))
        deck_update_index = next(
            index
            for index, event in enumerate(events)
            if isinstance(event, DeckUpdatedEvent)
        )
        tool_result = events[tool_result_index]
        deck_update = events[deck_update_index]

        assert deck_update_index == tool_result_index + 1
        assert tool_call.action_type == ActionType.MUTATE
        assert tool_call.status_label == "Baue das 80er-Deck"
        assert isinstance(tool_result, ToolResultEvent)
        assert isinstance(deck_update, DeckUpdatedEvent)
        assert tool_result.result == (
            '1 track reference(s) processed for Hitster deck "Deck".'
        )
        assert deck_update.deck_draft.name == "Deck"
        assert deck_update.deck_draft.tracks[0].title == "Take On Me"
        assert store.drain_deck_draft_updates() == []

    @pytest.mark.asyncio
    async def test_agent_passes_only_onboarding_tools_by_default(self) -> None:
        llm = _FakeLlm([_ChatResponse(completion="ok", tool_calls=[])])
        agent = Agent(llm=llm)

        _ = [event async for event in agent.stream("Hallo")]

        tool_names = {
            schema["function"]["name"] for schema in llm.tool_schema_batches[0]
        }
        assert agent.phase == Phase.ONBOARDING
        assert "ask_onboarding_question" in tool_names

    @pytest.mark.asyncio
    async def test_agent_uses_build_tools_when_started_in_build_phase(self) -> None:
        llm = _FakeLlm([_ChatResponse(completion="ok", tool_calls=[])])
        agent = Agent(llm=llm, phase=Phase.BUILD)

        _ = [event async for event in agent.stream("Bau mir ein Deck")]

        tool_names = {
            schema["function"]["name"] for schema in llm.tool_schema_batches[0]
        }
        assert agent.phase == Phase.BUILD
        assert "search_tracks" in tool_names
        assert "add_deck_tracks" in tool_names
        assert "create_deck" not in tool_names

    @pytest.mark.asyncio
    async def test_last_onboarding_question_suspends_run(self) -> None:
        tool_args = {
            "question": "Fuer wen ist die Playlist?",
            "hint": "Enge Zielgruppen machen das Deck spitzer.",
            "options": ["Freunde", "Familie", "Kolleg:innen"],
            "status": "Frage stellen",
            "is_last_question": True,
        }

        llm = _FakeLlm(
            [
                _ChatResponse(
                    completion="",
                    tool_calls=[
                        ToolCall(
                            id="call-1",
                            function={
                                "name": "ask_onboarding_question",
                                "arguments": json.dumps(tool_args),
                            },
                        )
                    ],
                ),
                _ChatResponse(completion="should-not-run", tool_calls=[]),
            ]
        )
        agent = Agent(llm=llm)

        events = [event async for event in agent.stream("Start")]

        assert not any(isinstance(event, ToolCallEvent) for event in events)
        assert not any(isinstance(event, ToolResultEvent) for event in events)
        suspended = next(
            event for event in events if isinstance(event, SuspendedForUserInputEvent)
        )
        assert suspended.hint == "Enge Zielgruppen machen das Deck spitzer."
        assert suspended.options == [
            "Freunde",
            "Familie",
            "Kolleg:innen",
        ]
        assert len(llm.tool_schema_batches) == 1

    @pytest.mark.asyncio
    async def test_non_last_onboarding_question_does_not_suspend_run(self) -> None:
        tool_args = {
            "question": "Fuer wen ist die Playlist?",
            "hint": "Die Zielgruppe hilft beim Schwierigkeitsgrad.",
            "options": ["Freunde", "Familie", "Kolleg:innen"],
            "status": "Frage stellen",
            "is_last_question": False,
        }

        llm = _FakeLlm(
            [
                _ChatResponse(
                    completion="",
                    tool_calls=[
                        ToolCall(
                            id="call-1",
                            function={
                                "name": "ask_onboarding_question",
                                "arguments": json.dumps(tool_args),
                            },
                        )
                    ],
                ),
                _ChatResponse(completion="done", tool_calls=[]),
            ]
        )
        agent = Agent(llm=llm)

        events = [event async for event in agent.stream("Start")]

        assert not any(isinstance(event, ToolCallEvent) for event in events)
        assert not any(isinstance(event, ToolResultEvent) for event in events)
        question = next(
            event for event in events if isinstance(event, QuestionAskedEvent)
        )
        assert question.hint == "Die Zielgruppe hilft beim Schwierigkeitsgrad."
        assert question.options == [
            "Freunde",
            "Familie",
            "Kolleg:innen",
        ]
        assert not any(
            isinstance(event, SuspendedForUserInputEvent) for event in events
        )
        assert len(llm.tool_schema_batches) == 2

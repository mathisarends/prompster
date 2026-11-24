import json
from collections.abc import AsyncIterator

import pytest
from agent.deck import Deck, DeckTrack
from agent.review import DeckCritic
from harnessed.models.pydantic_ai import PydanticAIModel
from pydantic_ai.messages import ModelMessage
from pydantic_ai.models.function import AgentInfo, FunctionModel


def _deck(*tracks: tuple[str, int]) -> Deck:
    return Deck(
        id="deck",
        name="Deck",
        tracks=tuple(
            DeckTrack(
                id=f"t{index}",
                title=f"Song {index}",
                artist=artist,
                year=year,
                spotify_uri=f"spotify:track:{index}",
            )
            for index, (artist, year) in enumerate(tracks)
        ),
    )


def _critic(calls: list[list[ModelMessage]], *, target_size: int = 50) -> DeckCritic:
    async def respond(
        messages: list[ModelMessage], _info: AgentInfo
    ) -> AsyncIterator[str]:
        calls.append(messages)
        yield json.dumps(
            {
                "assessment": "Zu viel ABBA.",
                "needs_refinement": True,
                "suggestions": [
                    {"issue": "ABBA", "action": "Replace two ABBA tracks."}
                ],
            }
        )

    model = PydanticAIModel(FunctionModel(stream_function=respond, model_name="critic"))
    return DeckCritic(model, target_size=target_size)


@pytest.mark.asyncio
async def test_empty_deck_is_not_reviewed() -> None:
    calls: list[list[ModelMessage]] = []

    review = await _critic(calls).review(None)

    assert review.triggered_llm is False
    assert calls == []


@pytest.mark.asyncio
async def test_balanced_deck_skips_the_llm() -> None:
    calls: list[list[ModelMessage]] = []
    deck = _deck(*((f"Artist {index}", 1960 + index * 8) for index in range(8)))

    review = await _critic(calls, target_size=8).review(deck)

    assert review.triggered_llm is False
    assert "Refinement recommended: no" in review.content
    assert calls == []


@pytest.mark.asyncio
async def test_concentrated_deck_gets_structured_llm_feedback() -> None:
    calls: list[list[ModelMessage]] = []
    deck = _deck(*(("ABBA", 1975 + index) for index in range(8)))

    review = await _critic(calls, target_size=20).review(deck, brief="Eine bunte Party")

    assert review.triggered_llm is True
    assert len(calls) == 1
    assert "Critic assessment: Zu viel ABBA." in review.content
    assert "- [ABBA] Replace two ABBA tracks." in review.content

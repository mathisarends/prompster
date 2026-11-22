import pytest
from agent.deck import DeckDraft, DeckDraftTrack, DeckStore
from agent.tools.handler.critic import DeckCritic
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel


def _store(*tracks: tuple[str, int]) -> DeckStore:
    return DeckStore(
        DeckDraft(
            name="Deck",
            tracks=[
                DeckDraftTrack(
                    title=f"Song {index}",
                    artist=artist,
                    year=year,
                    spotify_uri=f"spotify:track:{index}",
                )
                for index, (artist, year) in enumerate(tracks)
            ],
        )
    )


def _critic_model(calls: list[list[ModelMessage]]) -> FunctionModel:
    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        calls.append(messages)
        return ModelResponse(
            parts=[
                ToolCallPart(
                    info.output_tools[0].name,
                    {
                        "assessment": "Zu viel ABBA.",
                        "needs_refinement": True,
                        "suggestions": [
                            {"issue": "ABBA", "action": "Replace two ABBA tracks."}
                        ],
                    },
                )
            ]
        )

    return FunctionModel(respond, model_name="critic")


@pytest.mark.asyncio
async def test_empty_deck_is_not_reviewed() -> None:
    calls: list[list[ModelMessage]] = []
    critic = DeckCritic(_critic_model(calls), deck_store=DeckStore())

    result = await critic.review()

    assert result.triggered_llm is False
    assert calls == []


@pytest.mark.asyncio
async def test_balanced_deck_skips_the_llm() -> None:
    calls: list[list[ModelMessage]] = []
    tracks = [(f"Artist {index}", 1960 + index * 8) for index in range(8)]
    critic = DeckCritic(_critic_model(calls), deck_store=_store(*tracks), target_size=8)

    result = await critic.review()

    assert result.triggered_llm is False
    assert "Refinement recommended: no" in result.content
    assert calls == []


@pytest.mark.asyncio
async def test_concentrated_deck_gets_structured_llm_feedback() -> None:
    calls: list[list[ModelMessage]] = []
    tracks = [("ABBA", 1975 + index) for index in range(8)]
    critic = DeckCritic(_critic_model(calls), deck_store=_store(*tracks), target_size=20)

    result = await critic.review(brief="Eine bunte Party")

    assert result.triggered_llm is True
    assert len(calls) == 1
    assert "Critic assessment: Zu viel ABBA." in result.content
    assert "- [ABBA] Replace two ABBA tracks." in result.content

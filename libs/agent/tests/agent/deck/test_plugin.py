from collections.abc import Callable
from typing import Any
from uuid import NAMESPACE_URL, uuid5

import pytest
from agent.agent import Agent, Phase
from agent.deck import Deck, DeckTrack
from agent.research import FoundTrack
from harnessed.events import ToolCallFinishedEvent
from tests.agent.conftest import TAKE_ON_ME, FakeSpotify

_AFRICA = FoundTrack(
    uri="spotify:track:africa", title="Africa", artist="Toto", year=1982
)
_SEARCH = {"call-search": ("search_tracks", {"query": "80er"})}


def _deck_track(found: FoundTrack) -> DeckTrack:
    return DeckTrack(
        id=str(uuid5(NAMESPACE_URL, found.uri)),
        title=found.title,
        artist=found.artist,
        spotify_uri=found.uri,
    )


async def _tool_result(
    scripted_llm: Callable[..., Any],
    step: dict[str, tuple[str, dict[str, Any]]],
    *,
    deck: Deck | None = None,
    max_deck_tracks: int = 50,
) -> tuple[str, Agent]:
    llm = scripted_llm(_SEARCH, step, "Fertig.")
    agent = Agent(
        llm.model,
        phase=Phase.BUILD,
        deck=deck,
        max_deck_tracks=max_deck_tracks,
        spotify=FakeSpotify(TAKE_ON_ME, _AFRICA),
    )
    async with agent:
        events = [event async for event in agent.stream("Los")]
    finished = [e for e in events if isinstance(e, ToolCallFinishedEvent)]
    return finished[-1].result.text, agent


def _add(*tracks: FoundTrack) -> dict[str, tuple[str, dict[str, Any]]]:
    uris = [track.uri for track in tracks]
    return {"call-1": ("add_deck_tracks", {"uris": uris})}


@pytest.mark.asyncio
async def test_add_creates_the_missing_deck_and_skips_duplicates(
    scripted_llm: Callable[..., Any],
) -> None:
    result, agent = await _tool_result(scripted_llm, _add(TAKE_ON_ME, TAKE_ON_ME))

    assert result == (
        'Added 1 of 2 track(s) to Hitster deck "Deck" (1 total).'
        " The others were already in the deck."
    )
    assert agent.deck is not None
    assert [track.title for track in agent.deck.tracks] == ["Take On Me"]


@pytest.mark.asyncio
async def test_add_reports_when_the_deck_is_full(
    scripted_llm: Callable[..., Any],
) -> None:
    deck = Deck(id="d", name="Deck", tracks=(_deck_track(TAKE_ON_ME),))

    result, _ = await _tool_result(
        scripted_llm, _add(_AFRICA), deck=deck, max_deck_tracks=1
    )

    assert result == (
        'Added 0 of 1 track(s) to Hitster deck "Deck" (1 total).'
        " The deck is full (max 1); extra tracks were skipped."
    )


@pytest.mark.asyncio
async def test_replace_swaps_a_deck_track_for_a_found_one(
    scripted_llm: Callable[..., Any],
) -> None:
    first = _deck_track(TAKE_ON_ME)
    step = {
        "call-1": (
            "replace_deck_tracks",
            {"swaps": [{"track_id": first.id, "uri": _AFRICA.uri}]},
        )
    }

    result, agent = await _tool_result(
        scripted_llm, step, deck=Deck(id="d", name="Deck", tracks=(first,))
    )

    assert result == "1 track replacement(s) processed."
    assert agent.deck is not None
    assert [track.title for track in agent.deck.tracks] == ["Africa"]


@pytest.mark.asyncio
async def test_remove_drops_tracks_by_id(scripted_llm: Callable[..., Any]) -> None:
    first, second = _deck_track(TAKE_ON_ME), _deck_track(_AFRICA)
    step = {"call-1": ("remove_deck_tracks", {"track_ids": [second.id]})}

    result, agent = await _tool_result(
        scripted_llm, step, deck=Deck(id="d", name="Deck", tracks=(first, second))
    )

    assert result == "1 track(s) removed from Hitster deck."
    assert agent.deck is not None
    assert [track.id for track in agent.deck.tracks] == [first.id]

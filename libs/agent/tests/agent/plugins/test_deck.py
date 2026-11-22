from collections.abc import Callable
from typing import Any

import pytest
from agent.agent import Agent
from agent.deck import DeckDraft, DeckDraftTrack, DeckStore
from agent.events import ToolResultEvent
from agent.tools.params import AddDraftDeckTracksParams
from agent.views import Phase
from pydantic import ValidationError

_TAKE_ON_ME = "spotify:track:2WfaOiMkCvy7F5fcp2zZ8L"
_BILLIE_JEAN = "spotify:track:5ChkMS8OtdzJeqyybCc9R5"
_AFRICA = "spotify:track:2374M0fQpWi3dLnB54qaLX"


def _track(title: str, uri: str) -> DeckDraftTrack:
    return DeckDraftTrack(title=title, artist="Artist", year=1985, spotify_uri=uri)


def _cached_store() -> DeckStore:
    store = DeckStore()
    store.cache_tracks(
        [
            _track("Take On Me", _TAKE_ON_ME),
            _track("Billie Jean", _BILLIE_JEAN),
            _track("Africa", _AFRICA),
        ]
    )
    return store


def _add_call(*uris: str) -> dict[str, tuple[str, dict[str, Any]]]:
    return {
        "call-1": (
            "add_deck_tracks",
            {"tracks": [{"uri": uri} for uri in uris]},
        )
    }


async def _run_tool(
    scripted_llm: Callable[..., Any],
    store: DeckStore,
    step: dict[str, tuple[str, dict[str, Any]]],
) -> str:
    llm = scripted_llm(step, "Fertig.")
    agent = Agent(llm=llm.model, deck_store=store, phase=Phase.BUILD)
    events = [event async for event in agent.stream("Los")]
    return next(e.result for e in events if isinstance(e, ToolResultEvent))


def test_add_params_reject_non_track_uris() -> None:
    with pytest.raises(ValidationError, match="spotify:track:"):
        AddDraftDeckTracksParams(tracks=[{"uri": "spotify:album:not-a-track"}])


@pytest.mark.asyncio
async def test_add_creates_the_missing_draft_and_skips_duplicates(
    scripted_llm: Callable[..., Any],
) -> None:
    store = _cached_store()

    result = await _run_tool(scripted_llm, store, _add_call(_TAKE_ON_ME, _TAKE_ON_ME))

    assert result == (
        'Added 1 of 2 track(s) to Hitster deck "Deck" (1 total).'
        " The others were already in the deck."
    )
    assert store.draft is not None
    assert [track.title for track in store.draft.tracks] == ["Take On Me"]


@pytest.mark.asyncio
async def test_add_reports_when_the_deck_is_full(
    scripted_llm: Callable[..., Any],
) -> None:
    existing = _track("Take On Me", _TAKE_ON_ME)
    store = DeckStore(DeckDraft(name="Deck", tracks=[existing]), max_tracks=1)
    store.cache_tracks([_track("Billie Jean", _BILLIE_JEAN)])

    result = await _run_tool(scripted_llm, store, _add_call(_BILLIE_JEAN))

    assert result == (
        'Added 0 of 1 track(s) to Hitster deck "Deck" (1 total).'
        " The deck is full (max 1); extra tracks were skipped."
    )


@pytest.mark.asyncio
async def test_replace_accepts_track_ids_from_json(
    scripted_llm: Callable[..., Any],
) -> None:
    first = _track("Take On Me", _TAKE_ON_ME)
    store = DeckStore(DeckDraft(name="Deck", tracks=[first]))
    store.cache_tracks([_track("Africa", _AFRICA)])
    step = {
        "call-1": (
            "replace_deck_tracks",
            {"replacements": [{"old_id": str(first.id), "new_uri": _AFRICA}]},
        )
    }

    result = await _run_tool(scripted_llm, store, step)

    assert result == "1 track replacement(s) processed."
    assert store.draft is not None
    assert [track.title for track in store.draft.tracks] == ["Africa"]


@pytest.mark.asyncio
async def test_remove_accepts_track_ids_from_json(
    scripted_llm: Callable[..., Any],
) -> None:
    first = _track("Take On Me", _TAKE_ON_ME)
    second = _track("Billie Jean", _BILLIE_JEAN)
    store = DeckStore(DeckDraft(name="Deck", tracks=[first, second]))
    step = {"call-1": ("remove_deck_tracks", {"track_ids": [str(second.id)]})}

    result = await _run_tool(scripted_llm, store, step)

    assert result == "1 track(s) removed from Hitster deck."
    assert store.draft is not None
    assert [track.id for track in store.draft.tracks] == [first.id]

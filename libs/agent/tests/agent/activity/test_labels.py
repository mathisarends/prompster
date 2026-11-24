from agent.activity import ActionType
from agent.activity.labels import action_type, batch_label, status_label
from harnessed.models import ToolCall


def test_research_labels_are_derived_from_arguments() -> None:
    playlist = ToolCall(
        "get_spotify_playlist_tracks",
        {"playlist_id": "spotify:playlist:123", "playlist_name": "This Is ABBA"},
    )

    assert status_label(ToolCall("search_tracks", {"query": "ABBA"})) == (
        "Suche Tracks: ABBA"
    )
    assert status_label(ToolCall("search_playlists", {"query": "Italo Disco"})) == (
        "Suche Playlists: Italo Disco"
    )
    assert status_label(playlist) == "Hole Playlist-Tracks: This Is ABBA"


def test_long_query_is_shortened_in_the_label() -> None:
    label = status_label(ToolCall("search_tracks", {"query": "x" * 60}))

    assert label is not None
    assert label.endswith("...")
    assert len(label) <= len("Suche Tracks: ") + 32


def test_tool_without_labels_has_no_status_or_batch_label() -> None:
    call = ToolCall("remove_deck_tracks", {"track_ids": []})

    assert status_label(call) is None
    assert batch_label([call]) is None


def test_action_types_cover_known_tools_only() -> None:
    assert action_type("review_deck") is ActionType.SELF_REVIEW
    assert action_type("ask_onboarding_question") is None


def test_batch_label_prefers_the_explicit_sequence_label() -> None:
    calls = [
        ToolCall("add_deck_tracks", {"status": "Lege Tracks ab"}),
        ToolCall("add_deck_tracks", {"sequence_label": "Deck bauen"}),
    ]

    assert batch_label(calls) == "Deck bauen"


def test_batch_label_falls_back_to_a_derived_status() -> None:
    assert batch_label([ToolCall("search_tracks", {"query": "ABBA"})]) == (
        "Suche Tracks: ABBA"
    )

from agent.plugins.labels import action_type, sequence_label, status_label
from agent.tools.views import ActionType
from harnessed.models import ToolCall


def test_research_labels_are_derived_from_arguments() -> None:
    assert status_label(ToolCall("search_tracks", {"query": "ABBA"})) == (
        "Suche Tracks: ABBA"
    )
    assert status_label(ToolCall("search_playlists", {"query": "Italo Disco"})) == (
        "Suche Playlists: Italo Disco"
    )
    assert status_label(
        ToolCall(
            "get_spotify_playlist_tracks",
            {"playlist_id": "spotify:playlist:123", "playlist_name": "This Is ABBA"},
        )
    ) == ("Hole Playlist-Tracks: This Is ABBA")


def test_long_query_is_shortened_in_the_label() -> None:
    label = status_label(ToolCall("search_tracks", {"query": "x" * 60}))

    assert label is not None
    assert label.endswith("...")
    assert len(label) <= len("Suche Tracks: ") + 32


def test_tool_without_labels_has_no_status_or_sequence() -> None:
    call = ToolCall("remove_deck_tracks", {"track_ids": []})

    assert status_label(call) is None
    assert sequence_label([call]) is None


def test_action_types_cover_known_tools_only() -> None:
    assert action_type("review_deck") == ActionType.SELF_REVIEW
    assert action_type("unknown") is None


def test_sequence_label_prefers_the_explicit_block_label() -> None:
    calls = [
        ToolCall("add_deck_tracks", {"status": "Lege Tracks ab"}),
        ToolCall("add_deck_tracks", {"sequence_label": "Deck bauen"}),
    ]

    assert sequence_label(calls) == "Deck bauen"


def test_sequence_label_falls_back_to_a_derived_status() -> None:
    assert sequence_label([ToolCall("search_tracks", {"query": "ABBA"})]) == (
        "Suche Tracks: ABBA"
    )

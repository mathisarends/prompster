import pytest
from agent.deck.params import AddDeckTracksParams
from pydantic import ValidationError


def test_add_params_reject_non_track_uris() -> None:
    with pytest.raises(ValidationError, match="spotify:track:"):
        AddDeckTracksParams(tracks=[{"uri": "spotify:album:not-a-track"}])

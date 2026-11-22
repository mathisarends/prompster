"""Build the result previews an agent tool surfaces to the user.

A tool returns ``ActionResult`` with ``items`` — bare ``cover + title`` previews
of the first results it produced (the tracks a search found, the playlists it
looked through). This module maps the Spotify-domain shapes into those previews
and keeps the count bounded so persisted previews never grow unboundedly.
"""

from agent.deck import DeckDraftTrack
from agent.tools.handler.spotify import SpotifyPlaylistPreview
from agent.tools.views import ActionResultItem


def track_preview_items(tracks: list[DeckDraftTrack]) -> list[ActionResultItem]:
    return [
        ActionResultItem(
            title=track.title,
            cover_url=track.cover_url,
            artist=track.artist,
            track_uri=track.spotify_uri,
        )
        for track in tracks[:_RESULT_PREVIEW_LIMIT]
    ]


def playlist_preview_items(
    playlists: list[SpotifyPlaylistPreview],
) -> list[ActionResultItem]:
    return [
        ActionResultItem(title=playlist.name, cover_url=playlist.cover_url)
        for playlist in playlists[:_RESULT_PREVIEW_LIMIT]
    ]


# Cap how many results a single tool surfaces as previews — enough to give the
# user a sense of what was found without persisting an unbounded list.
_RESULT_PREVIEW_LIMIT = 10

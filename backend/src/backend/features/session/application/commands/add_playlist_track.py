from backend.features.session.application.events import (
    SessionEvent,
    SessionPlaylistSet,
    SessionPlaylistTrackAdded,
)
from backend.features.session.domain import Session


class AddPlaylistTrackHandler:
    async def handle(
        self,
        *,
        session: Session,
        title: str,
        artist: str,
        year: int | None = None,
        cover_url: str | None = None,
    ) -> tuple[SessionEvent, ...]:
        playlist_existed_before = session.playlist is not None
        track = session.add_track(
            title=title,
            artist=artist,
            year=year,
            cover_url=cover_url,
        )
        playlist = session.playlist

        if playlist is None:
            return ()

        if not playlist_existed_before:
            return (SessionPlaylistSet(playlist=playlist),)

        return (SessionPlaylistTrackAdded(playlist_id=playlist.id, track=track),)

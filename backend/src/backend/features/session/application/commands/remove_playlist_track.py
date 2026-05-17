from uuid import UUID

from backend.features.session.application.events import (
    SessionEvent,
    SessionPlaylistTrackRemoved,
)
from backend.features.session.domain import Session


class RemovePlaylistTrackHandler:
    async def handle(
        self,
        *,
        session: Session,
        track_id: UUID,
    ) -> tuple[SessionEvent, ...]:
        playlist = session.playlist
        session.remove_track(track_id=track_id)

        if playlist is None:
            return ()

        return (
            SessionPlaylistTrackRemoved(playlist_id=playlist.id, track_id=track_id),
        )

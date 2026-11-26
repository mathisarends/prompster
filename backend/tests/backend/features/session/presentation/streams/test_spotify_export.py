import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock
from uuid import UUID

import httpx2
import pytest
from spotifyify import RetryEvent

from backend.features.session.application import SessionSpotifyPlaylistExporter
from backend.features.session.application.spotify_playlist_exporter import (
    ExportedSpotifyPlaylist,
)
from backend.features.session.domain import SessionPlaylistEmptyError
from backend.features.session.presentation.streams.spotify_export import (
    SpotifyExportDoneEvent,
    SpotifyExportErrorEvent,
    spotify_export_events,
)
from backend.features.spotify.application.retry_reporting import report_retry


def make_retry() -> RetryEvent:
    return RetryEvent(
        method="POST",
        path="/playlists",
        response=httpx2.Response(429),
        retry_number=1,
        max_retries=3,
        retry_in_seconds=0.5,
        retry_at=datetime(2024, 1, 1, tzinfo=UTC),
    )


@pytest.mark.parametrize("stage", ["prepare", "execute"])
@pytest.mark.parametrize("expected", [True, False])
def test_export_errors_end_with_done_and_sanitize_unexpected_failures(stage, expected):
    exporter = Mock(spec=SessionSpotifyPlaylistExporter)
    error = (
        SessionPlaylistEmptyError("Playlist is empty")
        if expected
        else RuntimeError("private token")
    )
    getattr(exporter, stage).side_effect = error

    async def collect():
        return [
            event
            async for event in spotify_export_events(
                exporter, session_id=UUID(int=1), user_id=UUID(int=2)
            )
        ]

    events = asyncio.run(collect())
    assert events == [
        SpotifyExportErrorEvent(
            code="SessionPlaylistEmptyError" if expected else "InternalError",
            message=(
                "Playlist is empty"
                if expected
                else "Die Playlist konnte nicht zu Spotify exportiert werden."
            ),
        ),
        SpotifyExportDoneEvent(),
    ]
    if stage == "prepare":
        exporter.execute.assert_not_awaited()


def test_export_stream_delivers_retries_and_final_playlist():
    session_id, user_id = UUID(int=3), UUID(int=4)
    exporter = Mock(spec=SessionSpotifyPlaylistExporter)
    plan = object()
    exporter.prepare.return_value = plan

    async def execute(_):
        report_retry(make_retry())
        report_retry(make_retry())
        return ExportedSpotifyPlaylist(
            id="playlist",
            name="Test",
            description="",
            url="https://example.com",
            track_count=2,
        )

    exporter.execute = AsyncMock(side_effect=execute)

    async def collect():
        return [
            event
            async for event in spotify_export_events(
                exporter, session_id=session_id, user_id=user_id
            )
        ]

    events = asyncio.run(collect())
    assert [event.type for event in events] == [
        "spotify_export.retry",
        "spotify_export.retry",
        "spotify_export.completed",
        "done",
    ]
    assert events[0].retry_in_seconds == 0.5
    assert events[2].playlist.id == "playlist"
    assert events[2].playlist.track_count == 2
    exporter.prepare.assert_awaited_once_with(session_id=session_id, user_id=user_id)
    exporter.execute.assert_awaited_once_with(plan)


def test_closing_export_stream_cancels_and_awaits_execution():
    exporter = Mock(spec=SessionSpotifyPlaylistExporter)
    closed = False

    async def execute(_):
        nonlocal closed
        try:
            report_retry(make_retry())
            await asyncio.Event().wait()
        finally:
            closed = True

    exporter.execute = AsyncMock(side_effect=execute)

    async def run():
        stream = spotify_export_events(
            exporter, session_id=UUID(int=5), user_id=UUID(int=6)
        )
        event = await anext(stream)
        await stream.aclose()
        return event

    event = asyncio.run(run())

    assert event.type == "spotify_export.retry"
    assert closed

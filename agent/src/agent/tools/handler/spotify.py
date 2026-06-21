import logging
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Self

from pydantic import BaseModel
from spotifyify import (
    Image,
    Playlist,
    RetryEvent,
    SimplifiedAlbum,
    SimplifiedArtist,
    SimplifiedPlaylist,
    Spotifyify,
    Track,
)

from agent.deck import DeckDraftTrack
from agent.messages.rendering import (
    render_album_tag,
    render_playlist_tag,
    render_track_tag,
)
from agent.tools.params import (
    AlbumTracksParams,
    ArtistAlbumsParams,
    ArtistTopTracksParams,
    PlaylistIdParams,
    SearchParams,
)
from agent.tools.retry_reporting import report_retry

logger = logging.getLogger(__name__)


class SpotifyTrackLookupResult(BaseModel):
    content: str
    tracks: list[DeckDraftTrack]


class SpotifyPlaylistPreview(BaseModel):
    name: str
    cover_url: str | None = None


class SpotifyPlaylistLookupResult(BaseModel):
    content: str
    playlists: list[SpotifyPlaylistPreview]


class Spotify:
    def __init__(self, client: Spotifyify | None = None) -> None:
        self._client = client or Spotifyify(scopes=[])
        self._open = False

    async def open(self) -> None:
        if self._open:
            return
        await self._client.http.open()
        self._open = True

    async def close(self) -> None:
        if not self._open:
            return
        await self._client.close()
        self._open = False

    async def __aenter__(self) -> Self:
        await self.open()
        return self

    async def __aexit__(self, *_) -> None:
        await self.close()

    async def search_tracks(self, params: SearchParams) -> SpotifyTrackLookupResult:
        await self.open()
        query_limit = min(params.limit, 50)
        logger.info(
            "Spotify search_tracks: query=%r limit=%d",
            params.query,
            query_limit,
        )
        with self._retry_logging():
            page = await self._client.tracks.find(
                params.query,
                limit=query_limit,
            )
        tracks = page.items or []
        logger.info(
            "Spotify search_tracks: found=%d query=%r",
            len(tracks),
            params.query,
        )
        if not tracks:
            return SpotifyTrackLookupResult(content="No tracks found.", tracks=[])
        return _track_lookup_result(
            tracks,
            release_date_for=_track_release_date,
            cover_url_for=_track_cover_url,
        )

    async def search_albums(self, params: SearchParams) -> str:
        await self.open()
        query_limit = min(params.limit, 50)
        logger.info(
            "Spotify search_albums: query=%r limit=%d",
            params.query,
            query_limit,
        )
        with self._retry_logging():
            page = await self._client.albums.find(
                params.query,
                limit=query_limit,
            )
        albums = page.items or []
        logger.info(
            "Spotify search_albums: found=%d query=%r",
            len(albums),
            params.query,
        )
        if not albums:
            return "No albums found."
        return "\n".join(_format_album(album) for album in albums)

    async def search_playlists(
        self, params: SearchParams
    ) -> SpotifyPlaylistLookupResult:
        await self.open()
        query_limit = min(params.limit, 50)
        logger.info(
            "Spotify search_playlists: query=%r limit=%d",
            params.query,
            query_limit,
        )
        with self._retry_logging():
            page = await self._client.playlists.find(
                params.query,
                limit=query_limit,
            )
        playlists = [playlist for playlist in (page.items or []) if playlist]
        logger.info(
            "Spotify search_playlists: found=%d query=%r",
            len(playlists),
            params.query,
        )
        if not playlists:
            return SpotifyPlaylistLookupResult(
                content="No playlists found.", playlists=[]
            )
        return SpotifyPlaylistLookupResult(
            content="\n".join(_format_playlist(playlist) for playlist in playlists),
            playlists=[_playlist_preview(playlist) for playlist in playlists],
        )

    async def get_artist_albums(self, params: ArtistAlbumsParams) -> str:
        artist_id = _normalize_spotify_id(params.artist_id, "artist")
        await self.open()
        logger.info(
            "Spotify get_artist_albums: artist_id=%s include_groups=%s limit=%d",
            artist_id,
            params.include_groups,
            params.limit,
        )
        with self._retry_logging():
            page = await self._client.artists.albums(
                artist_id,
                include_groups=params.include_groups,
                limit=params.limit,
            )
        albums = page.items or []
        logger.info(
            "Spotify get_artist_albums: found=%d artist_id=%s",
            len(albums),
            artist_id,
        )
        if not albums:
            return "No albums found."
        return "\n".join(_format_album(album) for album in albums)

    async def get_artist_top_tracks(
        self,
        params: ArtistTopTracksParams,
    ) -> SpotifyTrackLookupResult:
        artist_id = _normalize_spotify_id(params.artist_id, "artist")
        await self.open()
        logger.info(
            "Spotify get_artist_top_tracks: artist_id=%s market=%s",
            artist_id,
            params.country,
        )
        with self._retry_logging():
            tracks = await self._client.artists.top_tracks(
                artist_id,
                market=params.country,
            )
        logger.info(
            "Spotify get_artist_top_tracks: found=%d artist_id=%s",
            len(tracks),
            artist_id,
        )
        if not tracks:
            return SpotifyTrackLookupResult(content="No top tracks found.", tracks=[])
        return _track_lookup_result(
            tracks,
            release_date_for=_track_release_date,
            cover_url_for=_track_cover_url,
        )

    async def get_album_tracks(
        self,
        params: AlbumTracksParams,
    ) -> SpotifyTrackLookupResult:
        album_id = _normalize_spotify_id(params.album_id, "album")
        await self.open()
        logger.info("Spotify get_album_tracks: album_id=%s", album_id)
        with self._retry_logging():
            album = await self._client.albums.get(album_id)
            page = await self._client.albums.tracks(album_id, limit=50, offset=0)
        tracks = page.items or []
        logger.info(
            "Spotify get_album_tracks: found=%d album_id=%s",
            len(tracks),
            album_id,
        )
        if not tracks:
            return SpotifyTrackLookupResult(content="No tracks found.", tracks=[])
        album_cover_url = _cover_url(album.images)
        return _track_lookup_result(
            tracks,
            release_date_for=lambda _: album.release_date,
            cover_url_for=lambda _: album_cover_url,
        )

    async def get_playlist_tracks(
        self,
        params: PlaylistIdParams,
    ) -> SpotifyTrackLookupResult:
        playlist_id = _normalize_spotify_id(params.playlist_id, "playlist")
        await self.open()
        logger.info("Spotify get_playlist_tracks: playlist_id=%s", playlist_id)
        with self._retry_logging():
            tracks = await self._get_playlist_tracks(playlist_id)
        logger.info(
            "Spotify get_playlist_tracks: found=%d playlist_id=%s",
            len(tracks),
            playlist_id,
        )
        if not tracks:
            return SpotifyTrackLookupResult(content="Playlist is empty.", tracks=[])
        return _track_lookup_result(
            tracks,
            release_date_for=_track_release_date,
            cover_url_for=_track_cover_url,
        )

    async def _get_playlist_tracks(self, playlist_id: str) -> list[Track]:
        tracks: list[Track] = []
        offset = 0
        limit = 100

        while True:
            page = await self._client.playlists.tracks(
                playlist_id,
                limit=limit,
                offset=offset,
                additional_types=["track"],
            )
            for playlist_item in page.items or []:
                item = playlist_item.item or playlist_item.track
                if item is not None and getattr(item, "type", None) == "track":
                    tracks.append(item)

            if not page.next:
                break
            offset += limit

        return tracks

    @contextmanager
    def _retry_logging(self) -> Iterator[None]:
        with self._client.retry_hook(_log_retry):
            yield


def _log_retry(event: RetryEvent) -> None:
    logger.warning(
        "Retrying Spotify request: method=%s path=%s status_code=%d "
        "retry_in_seconds=%s retry=%d/%d",
        event.method.value,
        event.path,
        event.status_code,
        event.retry_in_seconds,
        event.retry_number,
        event.max_retries,
    )
    report_retry(event)


def _playlist_track_count(playlist: Playlist | SimplifiedPlaylist) -> int:
    tracks = playlist.items or playlist.tracks
    return tracks.total if tracks and tracks.total is not None else 0


def _normalize_spotify_id(value: str, resource_type: str) -> str:
    prefix = f"spotify:{resource_type}:"
    if value.startswith(prefix):
        return value[len(prefix) :]

    marker = f"/{resource_type}/"
    if marker in value:
        tail = value.split(marker, 1)[1]
        return tail.split("?", 1)[0].split("/", 1)[0]

    return value


def _artist_names(artists: list[SimplifiedArtist] | None) -> str:
    names = [artist.name for artist in (artists or []) if artist and artist.name]
    return ", ".join(names) if names else "Unknown artist"


def _track_title(track: Track) -> str:
    return track.name or "Unknown title"


def _release_year(release_date: str | None) -> int:
    if release_date and len(release_date) >= 4 and release_date[:4].isdigit():
        return int(release_date[:4])
    return 0


def _track_release_date(track: Track) -> str | None:
    return track.album.release_date if track.album else None


def _track_cover_url(track: Track) -> str | None:
    return _cover_url(track.album.images) if track.album else None


def _cover_url(images: list[Image] | None) -> str | None:
    if not images:
        return None
    return images[0].url


def _track_lookup_result(
    tracks: list[Track],
    *,
    release_date_for: Callable[[Track], str | None],
    cover_url_for: Callable[[Track], str | None],
) -> SpotifyTrackLookupResult:
    lines: list[str] = []
    draft_tracks: list[DeckDraftTrack] = []

    for _, track in enumerate(tracks):
        release_date = release_date_for(track)
        cover_url = cover_url_for(track)
        draft_track = _deck_draft_track(track, release_date, cover_url)
        if draft_track.spotify_uri is not None:
            draft_tracks.append(draft_track)
            lines.append(
                render_track_tag(
                    draft_track,
                    identity_attr="uri",
                    identity_value=draft_track.spotify_uri,
                )
            )

    return SpotifyTrackLookupResult(content="\n".join(lines), tracks=draft_tracks)


def _deck_draft_track(
    track: Track,
    release_date: str | None,
    cover_url: str | None,
) -> DeckDraftTrack:
    return DeckDraftTrack(
        title=_track_title(track),
        artist=_artist_names(track.artists),
        year=_release_year(release_date) or None,
        spotify_uri=(
            track.uri if track.uri and track.uri.startswith("spotify:track:") else None
        ),
        cover_url=cover_url,
    )


def _format_album(album: SimplifiedAlbum) -> str:
    return render_album_tag(
        uri=album.uri,
        name=album.name,
        artist=_artist_names(album.artists),
        year=_release_year(album.release_date),
        track_count=album.total_tracks,
    )


def _format_playlist(playlist: Playlist | SimplifiedPlaylist) -> str:
    return render_playlist_tag(
        id=playlist.id,
        name=playlist.name,
        track_count=_playlist_track_count(playlist),
    )


def _playlist_preview(
    playlist: Playlist | SimplifiedPlaylist,
) -> SpotifyPlaylistPreview:
    return SpotifyPlaylistPreview(
        name=playlist.name or "Unknown playlist",
        cover_url=_cover_url(playlist.images),
    )

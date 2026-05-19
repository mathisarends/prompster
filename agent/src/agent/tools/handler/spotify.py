from typing import Self

from spotifyify import PagingPlaylistTrack, Spotifyify, Track

from agent.tools.views import (
    AlbumTracksParams,
    ArtistAlbumsParams,
    ArtistTopTracksParams,
    PlaylistIdParams,
    SearchParams,
)


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

    async def search_tracks(self, params: SearchParams) -> str:
        await self.open()
        page = await self._client.tracks.find(params.query, limit=min(params.limit, 50))
        tracks = page.items or []
        if not tracks:
            return "No tracks found."
        return "\n".join(
            _format_track(index + 1, track) for index, track in enumerate(tracks)
        )

    async def search_albums(self, params: SearchParams) -> str:
        await self.open()
        page = await self._client.albums.find(params.query, limit=min(params.limit, 50))
        albums = page.items or []
        if not albums:
            return "No albums found."
        return "\n".join(
            _format_album(index + 1, album) for index, album in enumerate(albums)
        )

    async def search_playlists(self, params: SearchParams) -> str:
        await self.open()
        page = await self._client.playlists.find(
            params.query,
            limit=min(params.limit, 50),
        )
        playlists = [playlist for playlist in (page.items or []) if playlist]
        if not playlists:
            return "No playlists found."
        return "\n".join(
            f"{index + 1}. {playlist.name} ({_playlist_track_count(playlist)} tracks)"
            f"  id={playlist.id}  url={_playlist_url(playlist)}"
            for index, playlist in enumerate(playlists)
        )

    async def get_artist_albums(self, params: ArtistAlbumsParams) -> str:
        artist_id = _normalize_spotify_id(params.artist_id, "artist")
        await self.open()
        page = await self._client.artists.albums(
            artist_id,
            include_groups=params.include_groups,
            limit=params.limit,
        )
        albums = page.items or []
        if not albums:
            return "No albums found."
        return "\n".join(
            _format_album(index + 1, album) for index, album in enumerate(albums)
        )

    async def get_artist_top_tracks(self, params: ArtistTopTracksParams) -> str:
        artist_id = _normalize_spotify_id(params.artist_id, "artist")
        await self.open()
        tracks = await self._client.artists.top_tracks(artist_id, market=params.country)
        if not tracks:
            return "No top tracks found."
        return "\n".join(
            _format_track(index + 1, track) for index, track in enumerate(tracks)
        )

    async def get_album_tracks(self, params: AlbumTracksParams) -> str:
        album_id = _normalize_spotify_id(params.album_id, "album")
        await self.open()
        album = await self._client.albums.get(album_id)
        page = await self._client.albums.tracks(album_id, limit=50, offset=0)
        tracks = page.items or []
        if not tracks:
            return "No tracks found."
        return "\n".join(
            _format_track(
                index + 1,
                track,
                fallback_release_date=album.release_date,
            )
            for index, track in enumerate(tracks)
        )

    async def get_playlist_tracks(self, params: PlaylistIdParams) -> str:
        playlist_id = _normalize_spotify_id(params.playlist_id, "playlist")
        await self.open()
        tracks = await self._get_playlist_tracks(playlist_id)
        if not tracks:
            return "Playlist is empty."
        return "\n".join(
            _format_track(index + 1, track) for index, track in enumerate(tracks)
        )

    async def _get_playlist_tracks(self, playlist_id: str) -> list[Track]:
        tracks: list[Track] = []
        offset = 0
        limit = 100

        while True:
            data = (
                await self._client.http.get(
                    f"/playlists/{playlist_id}/tracks",
                    params={
                        "offset": offset,
                        "limit": limit,
                        "additional_types": "track",
                    },
                    require_user=False,
                )
                or {}
            )
            page = PagingPlaylistTrack.model_validate(data)
            for playlist_item in page.items or []:
                item = playlist_item.item or playlist_item.track
                if item is not None and getattr(item, "type", None) == "track":
                    tracks.append(item)

            if not page.next:
                break
            offset += limit

        return tracks


def _playlist_track_count(playlist) -> int:
    tracks = playlist.items or playlist.tracks
    return tracks.total if tracks else 0


def _normalize_spotify_id(value: str, resource_type: str) -> str:
    prefix = f"spotify:{resource_type}:"
    if value.startswith(prefix):
        return value[len(prefix) :]

    marker = f"/{resource_type}/"
    if marker in value:
        tail = value.split(marker, 1)[1]
        return tail.split("?", 1)[0].split("/", 1)[0]

    return value


def _artist_names(artists) -> str:
    names = [artist.name for artist in (artists or []) if artist and artist.name]
    return ", ".join(names) if names else "Unknown artist"


def _track_title(track) -> str:
    return track.name or "Unknown title"


def _release_year(release_date: str | None) -> int:
    if release_date and len(release_date) >= 4 and release_date[:4].isdigit():
        return int(release_date[:4])
    return 0


def _track_url(track) -> str:
    if track.external_urls and track.external_urls.spotify:
        return track.external_urls.spotify
    if track.uri and track.uri.startswith("spotify:track:"):
        track_id = track.uri.removeprefix("spotify:track:")
        return f"https://open.spotify.com/track/{track_id}"
    return ""


def _playlist_url(playlist) -> str:
    if playlist.external_urls and playlist.external_urls.spotify:
        return playlist.external_urls.spotify
    if playlist.id:
        return f"https://open.spotify.com/playlist/{playlist.id}"
    return ""


def _format_track(index: int, track, fallback_release_date: str | None = None) -> str:
    artists = track.artists or []
    artist_uris = ", ".join(artist.uri for artist in artists if artist.uri)
    date = (
        track.album.release_date
        if track.album and track.album.release_date
        else fallback_release_date
    )
    return (
        f"{index}. {_track_title(track)}"
        f" – {_artist_names(artists)}"
        f" ({_release_year(date)})"
        f"  uri={track.uri or 'n/a'}  artist_uris=[{artist_uris}]"
    )


def _format_album(index: int, album) -> str:
    artists = album.artists or []
    return (
        f"{index}. {album.name} – {_artist_names(artists)}"
        f" ({_release_year(album.release_date)}, {album.total_tracks} tracks)"
        f"  uri={album.uri}"
    )

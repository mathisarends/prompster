from pathlib import Path
from typing import Self

from agentory import Agent, Inject, Tools
from llmify import ChatOpenAI
from spotifyify import PagingPlaylistTrack, Spotifyify, SpotifyScope, Track

from agent.helpers import (
    chunked,
    format_album,
    format_track,
    normalize_spotify_id,
    playlist_url,
)
from agent.views import (
    AlbumTracksParams,
    ArtistAlbumsParams,
    ArtistTopTracksParams,
    CreatePlaylistParams,
    PlaylistIdParams,
    PlaylistTracksMutationParams,
    SearchParams,
)

_SYSTEM_PROMPT = (Path(__file__).parent / "system_prompt.md").read_text(
    encoding="utf-8"
)

# TODO: Playlists muss hier ein gedankliches Konstrukt sein was wir hier injeten (Datenstruktur nirgendwo bei spotify persistiert)

# Nicht ohne User-Scopes:

# create_playlist — braucht user-read-private (für /me) + PLAYLIST_MODIFY_*
# add_tracks_to_playlist — PLAYLIST_MODIFY_*
# remove_tracks_from_playlist — PLAYLIST_MODIFY_*
# clear_playlist — PLAYLIST_MODIFY_*
# get_playlist_tracks auf privaten Playlists — PLAYLIST_READ_PRIVATE


class HitsterAgent:
    def __init__(self) -> None:
        self._instructions = _SYSTEM_PROMPT
        self._tools = Tools()
        self._spotify_open = False
        self._spotify = Spotifyify(
            scopes=[
                # Needed by spotifyify.playlists.create() which resolves /me first.
                "user-read-private",
                SpotifyScope.PLAYLIST_READ_PRIVATE,
                SpotifyScope.PLAYLIST_MODIFY_PUBLIC,
                SpotifyScope.PLAYLIST_MODIFY_PRIVATE,
            ]
        )
        self._register_tools()
        self._agent = Agent(
            instructions=self._instructions,
            tools=self._tools,
            llm=ChatOpenAI(model="gpt-5.4"),
            injectables=[self._spotify],
        )

    def stream(self, user_input: str):
        return self._agent.stream(user_input)

    def reset(self) -> None:
        self._agent = Agent(
            instructions=self._instructions,
            tools=self._tools,
            llm=self._agent.llm,
            injectables=[self._spotify, self._deck_renderer],
        )

    async def open(self) -> None:
        if self._spotify_open:
            return
        await self._spotify.http.open()
        self._spotify_open = True

    async def __aenter__(self) -> Self:
        await self.open()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def close(self) -> None:
        if not self._spotify_open:
            return
        await self._spotify.close()
        self._spotify_open = False

    async def _require_open_spotify(self, spotify: Spotifyify) -> Spotifyify:
        if spotify is not self._spotify:
            msg = "Unexpected Spotify client instance injected into HitsterAgent."
            raise RuntimeError(msg)
        if not self._spotify_open:
            msg = (
                "Spotify client is not open. Use 'await agent.open()' "
                "or 'async with HitsterAgent(...) as agent'."
            )
            raise RuntimeError(msg)
        return spotify

    def _register_tools(self) -> None:
        tools = self._tools

        @tools.action(
            description="Search Spotify for tracks matching a query. Returns title, artist, year and URI for each result.",
            status_label=lambda params: f"Suche nach '{params.query}'",
            params=SearchParams,
        )
        async def search_tracks(
            spotify: Inject[Spotifyify], params: SearchParams
        ) -> str:
            sp = await self._require_open_spotify(spotify)
            page = await sp.tracks.find(params.query, limit=min(params.limit, 50))
            tracks = page.items or []
            if not tracks:
                return "No tracks found."
            return "\n".join(
                format_track(index + 1, track) for index, track in enumerate(tracks)
            )

        @tools.action(
            description="Search Spotify for albums matching a query. Returns album name, artist, year, track count and URI.",
            status_label=lambda params: f"Alben suchen: '{params.query}'",
            params=SearchParams,
        )
        async def search_albums(
            spotify: Inject[Spotifyify], params: SearchParams
        ) -> str:
            sp = await self._require_open_spotify(spotify)
            page = await sp.albums.find(params.query, limit=min(params.limit, 50))
            albums = page.items or []
            if not albums:
                return "No albums found."
            return "\n".join(
                format_album(index + 1, album) for index, album in enumerate(albums)
            )

        @tools.action(
            description="Search Spotify for public playlists matching a query. Returns playlist name, track count and ID.",
            status_label=lambda params: f"Playlists suchen: '{params.query}'",
            params=SearchParams,
        )
        async def search_playlists(
            spotify: Inject[Spotifyify], params: SearchParams
        ) -> str:
            sp = await self._require_open_spotify(spotify)
            page = await sp.playlists.find(params.query, limit=min(params.limit, 50))
            playlists = [playlist for playlist in (page.items or []) if playlist]
            if not playlists:
                return "No playlists found."
            return "\n".join(
                f"{index + 1}. {playlist.name} ({(playlist.items or playlist.tracks).total if (playlist.items or playlist.tracks) else 0} tracks)"
                f"  id={playlist.id}  url={playlist_url(playlist)}"
                for index, playlist in enumerate(playlists)
            )

        @tools.action(
            description="Get albums by an artist (pass artist URI or ID). Returns album name, year, track count.",
            status_label="Künstler-Alben laden",
            params=ArtistAlbumsParams,
        )
        async def get_artist_albums(
            spotify: Inject[Spotifyify],
            params: ArtistAlbumsParams,
        ) -> str:
            artist_id = normalize_spotify_id(params.artist_id, "artist")
            sp = await self._require_open_spotify(spotify)
            page = await sp.artists.albums(
                artist_id,
                include_groups=params.include_groups,
                limit=params.limit,
            )
            albums = page.items or []
            if not albums:
                return "No albums found."
            return "\n".join(
                format_album(index + 1, album) for index, album in enumerate(albums)
            )

        @tools.action(
            description="Get an artist's top tracks. Pass artist URI or ID. Returns title, artist, year and URI.",
            status_label="Top-Tracks laden",
            params=ArtistTopTracksParams,
        )
        async def get_artist_top_tracks(
            spotify: Inject[Spotifyify],
            params: ArtistTopTracksParams,
        ) -> str:
            artist_id = normalize_spotify_id(params.artist_id, "artist")
            sp = await self._require_open_spotify(spotify)
            tracks = await sp.artists.top_tracks(artist_id, market=params.country)
            if not tracks:
                return "No top tracks found."
            return "\n".join(
                format_track(index + 1, track) for index, track in enumerate(tracks)
            )

        @tools.action(
            description="Get all tracks of an album by album URI or ID. Returns title, artist, year and URI.",
            status_label="Album-Tracks laden",
            params=AlbumTracksParams,
        )
        async def get_album_tracks(
            spotify: Inject[Spotifyify], params: AlbumTracksParams
        ) -> str:
            album_id = normalize_spotify_id(params.album_id, "album")
            sp = await self._require_open_spotify(spotify)
            album = await sp.albums.get(album_id)
            page = await sp.albums.tracks(album_id, limit=50, offset=0)
            tracks = page.items or []
            if not tracks:
                return "No tracks found."
            return "\n".join(
                format_track(index + 1, track, fallback_release_date=album.release_date)
                for index, track in enumerate(tracks)
            )

        @tools.action(
            description="Create a Spotify playlist for the current user. Returns the playlist ID and URL.",
            status_label=lambda params: f"Playlist erstellen: '{params.name}'",
            params=CreatePlaylistParams,
        )
        async def create_playlist(
            spotify: Inject[Spotifyify], params: CreatePlaylistParams
        ) -> str:
            prefixed_name = "Hitster Deck: " + params.name
            sp = await self._require_open_spotify(spotify)
            playlist = await sp.playlists.create(
                prefixed_name, description=params.description
            )
            return (
                f"Created playlist '{playlist.name}'"
                f" — id={playlist.id}  url={playlist_url(playlist)}"
            )

        @tools.action(
            description="Add tracks to an existing Spotify playlist by playlist ID and a list of Spotify track URIs.",
            status_label=lambda params: f"{len(params.track_uris)} Tracks hinzufügen",
            params=PlaylistTracksMutationParams,
        )
        async def add_tracks_to_playlist(
            spotify: Inject[Spotifyify],
            params: PlaylistTracksMutationParams,
        ) -> str:
            invalid = [
                u for u in params.track_uris if not u.startswith("spotify:track:")
            ]
            if invalid:
                return f"Error: invalid track URIs (must start with 'spotify:track:'): {invalid}"

            playlist_id = normalize_spotify_id(params.playlist_id, "playlist")
            sp = await self._require_open_spotify(spotify)
            for chunk in chunked(params.track_uris, 100):
                await sp.playlists.add(playlist_id, chunk)
            return f"Added {len(params.track_uris)} track(s) to playlist {playlist_id}."

        @tools.action(
            description="Get all tracks of an existing Spotify playlist. Returns title, artist, year and URI per track.",
            status_label="Playlist-Tracks laden",
            params=PlaylistIdParams,
        )
        async def get_playlist_tracks(
            spotify: Inject[Spotifyify], params: PlaylistIdParams
        ) -> str:
            playlist_id = normalize_spotify_id(params.playlist_id, "playlist")
            sp = await self._require_open_spotify(spotify)
            tracks = await self._get_playlist_tracks(sp, playlist_id)
            if not tracks:
                return "Playlist is empty."
            return "\n".join(
                format_track(index + 1, track) for index, track in enumerate(tracks)
            )

        @tools.action(
            description="Remove specific tracks from a Spotify playlist by playlist ID and a list of track URIs.",
            status_label=lambda params: f"{len(params.track_uris)} Tracks entfernen",
            params=PlaylistTracksMutationParams,
        )
        async def remove_tracks_from_playlist(
            spotify: Inject[Spotifyify],
            params: PlaylistTracksMutationParams,
        ) -> str:
            playlist_id = normalize_spotify_id(params.playlist_id, "playlist")
            sp = await self._require_open_spotify(spotify)
            for chunk in chunked(params.track_uris, 100):
                await sp.playlists.remove(playlist_id, chunk)
            return (
                f"Removed {len(params.track_uris)} track(s) from playlist "
                f"{playlist_id}."
            )

        @tools.action(
            description="Remove all tracks from a Spotify playlist (clear it completely).",
            status_label="Playlist leeren",
            params=PlaylistIdParams,
        )
        async def clear_playlist(
            spotify: Inject[Spotifyify], params: PlaylistIdParams
        ) -> str:
            playlist_id = normalize_spotify_id(params.playlist_id, "playlist")
            sp = await self._require_open_spotify(spotify)
            tracks = await self._get_playlist_tracks(sp, playlist_id)
            uris = [track.uri for track in tracks if track.uri]
            for chunk in chunked(uris, 100):
                await sp.playlists.remove(playlist_id, chunk)
            return f"Playlist {playlist_id} cleared."

        # @tools.action(
        #     description="Generate Hitster cards as a PDF for the given Spotify playlist. Returns the path to the generated PDF.",
        #     status_label="Karten generieren...",
        #     params=GenerateCardsParams,
        # )
        # async def generate_cards(
        #     spotify: Inject[Spotifyify],
        #     deck_renderer: Inject[DeckRenderer],
        #     params: GenerateCardsParams,
        # ) -> str:
        #     playlist_id = normalize_spotify_id(params.playlist_id, "playlist")
        #     sp = await self._require_open_spotify(spotify)
        #     tracks = await self._get_playlist_tracks(sp, playlist_id)
        #     if not tracks:
        #         return "Playlist is empty — no cards generated."
        #     cards = [
        #         TrackCard(
        #             title=track_title(t),
        #             artist_names=artist_names(t.artists),
        #             release_year=release_year(
        #                 t.album.release_date if t.album else None
        #             ),
        #             spotify_url=track_url(t),
        #         )
        #         for t in tracks
        #     ]
        #     output = Path.cwd() / "output" / "hitster-deck.pdf"
        #     output.parent.mkdir(exist_ok=True)
        #     await deck_renderer.render(cards, output)
        #     return f"Cards generated: {output}  ({len(cards)} cards)"

    @staticmethod
    async def _get_playlist_tracks(
        spotify: Spotifyify, playlist_id: str
    ) -> list[Track]:
        tracks: list[Track] = []
        offset = 0
        limit = 100

        while True:
            data = (
                await spotify.http.get(
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

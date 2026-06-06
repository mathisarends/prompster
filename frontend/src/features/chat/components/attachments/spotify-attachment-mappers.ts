import type {
  SpotifyArtistResponse,
  SpotifyPlaylistResponse,
} from "@/api/generated/model";

import type { ChatAttachment } from "./attachment-types";

export const playlistToAttachment = (
  playlist: SpotifyPlaylistResponse,
): ChatAttachment => ({
  id: playlist.id,
  kind: "spotify-playlist",
  title: playlist.name,
  subtitle: playlist.owner ?? undefined,
  imageUrl: playlist.coverUrl,
  spotifyId: playlist.id,
});

export const artistToAttachment = (
  artist: SpotifyArtistResponse,
): ChatAttachment => ({
  id: artist.id,
  kind: "spotify-artist",
  title: artist.name,
  subtitle: artist.genres?.slice(0, 2).join(", ") || undefined,
  imageUrl: artist.imageUrl,
  spotifyId: artist.id,
});

import { useMemo, useState } from "react";
import { ListMusic } from "lucide-react";

import type { PlaylistTrackResponse } from "@/api/generated/model";
import { useGetMe } from "@/api/generated/user-api";
import { ChatWorkspacePanel } from "@/components/chat/chat-workspace-panel";
import {
  DeckPlaylist,
  type DeckPlaylistController,
} from "@/components/deck/deck-playlist";
import { SpotifyConnectDialog } from "@/components/deck/spotify-connect-dialog";
import { useSpotifyOAuthPopup } from "@/hooks/useSpotifyOAuthPopup";
import { useSpotifyPlayer } from "@/hooks/useSpotifyPlayer";

type DeckWorkspaceViewProps = {
  playlist: {
    name?: string | null;
    tracks: PlaylistTrackResponse[];
  };
  onRemoveTrack?: (trackId: string) => Promise<void>;
};

export const DeckWorkspaceView = ({
  playlist,
  onRemoveTrack,
}: DeckWorkspaceViewProps) => {
  const { data: me, isLoading: isMeLoading } = useGetMe();
  const { isSpotifyOAuthLoading, openSpotifyOAuthPopup } =
    useSpotifyOAuthPopup();
  const [volume, setVolume] = useState(72);
  const {
    state: playerState,
    playTrack,
    pause,
    resume,
    seek,
    setVolume: setSpotifyVolume,
  } = useSpotifyPlayer({ enabled: Boolean(me?.spotifyConnected) });

  const tracks = useMemo(
    () =>
      playlist.tracks.map((track) => ({
        id: track.id,
        title: track.title,
        artist: track.artist,
        year: track.year?.toString() ?? "",
        durationSeconds: 0,
        coverUrl: track.coverUrl ?? "",
        spotifyUri: track.spotifyUri ?? null,
      })),
    [playlist.tracks],
  );

  const activeTrackId = useMemo(
    () =>
      tracks.find((track) => track.spotifyUri === playerState.currentTrackUri)
        ?.id ?? null,
    [playerState.currentTrackUri, tracks],
  );

  const controller = useMemo<DeckPlaylistController>(
    () => ({
      isPlaying: !playerState.isPaused && Boolean(playerState.currentTrackUri),
      activeTrackId,
      positionSeconds: playerState.positionMs / 1000,
      durationSeconds: playerState.durationMs / 1000,
      volume,
      onPlayTrack: (trackId: string) => {
        const track = tracks.find((candidate) => candidate.id === trackId);
        if (!track?.spotifyUri) {
          return;
        }

        void playTrack(track.spotifyUri);
      },
      onPause: () => {
        void pause();
      },
      onResume: () => {
        void resume();
      },
      onSeek: (seconds: number) => {
        void seek(Math.round(seconds * 1000));
      },
      onVolumeChange: (nextVolume: number) => {
        setVolume(nextVolume);
        void setSpotifyVolume(nextVolume / 100);
      },
    }),
    [
      activeTrackId,
      pause,
      playTrack,
      playerState.currentTrackUri,
      playerState.durationMs,
      playerState.isPaused,
      playerState.positionMs,
      resume,
      seek,
      setSpotifyVolume,
      tracks,
      volume,
    ],
  );

  const connectRequired =
    (!isMeLoading && !me?.spotifyConnected) ||
    playerState.status === "auth-error";

  return (
    <>
      <SpotifyConnectDialog
        open={connectRequired}
        onConnect={openSpotifyOAuthPopup}
        isConnecting={isSpotifyOAuthLoading}
      />

      <ChatWorkspacePanel
        header={
          <div className="flex items-center gap-1.5 px-1.5 py-2 text-sm font-semibold">
            <ListMusic className="size-4" />
            Liste
          </div>
        }
      >
        <div className="flex min-h-0 flex-1 flex-col pt-2">
          {playerState.status === "premium-required" ? (
            <div className="mb-3 rounded-md border border-amber-300/20 bg-amber-500/10 px-3 py-2 text-xs text-amber-100">
              Spotify Premium ist erforderlich, um Web-Playback im Browser zu
              nutzen.
            </div>
          ) : null}

          <DeckPlaylist
            initialTracks={tracks}
            showHeader={false}
            allowLocalRemoval={false}
            onRemoveTrack={onRemoveTrack}
            controller={controller}
          />
        </div>
      </ChatWorkspacePanel>
    </>
  );
};

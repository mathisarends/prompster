import { useCallback, useEffect, useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import type {
  SpotifyTrackResponse,
  UserCurationEventResponse,
} from "@/api/generated/model";
import { getGetMeQueryKey, useGetMe } from "@/api/generated/user-api";
import type { DeckPlaylistController } from "@/hooks/usePlaybackState";
import { useSpotifyPlayer } from "@/hooks/useSpotifyPlayer";
import type { PlaylistTrack } from "@/lib/playlist-track";

export type SpotifyMode = "loading" | "disconnected" | "non-premium" | "ready";

export type CurationTrackPlayerBridge = {
  activeTrackUri: string | null;
  isPlaying: boolean;
  onTogglePlayback: (event: UserCurationEventResponse) => void;
};

type UseDeckPlayerControllerOptions = {
  tracks: PlaylistTrack[];
  onCurationTrackPlayerChange?: (
    bridge: CurationTrackPlayerBridge | null,
  ) => void;
};

type UseDeckPlayerControllerResult = {
  spotifyMode: SpotifyMode;
  controller: DeckPlaylistController | undefined;
  showPlaybackControls: boolean;
  showPremiumRequiredHint: boolean;
  previewTrack: PlaylistTrack | null;
  previewSpotifyTrack: (track: SpotifyTrackResponse) => void;
};

export const useDeckPlayerController = ({
  tracks,
  onCurationTrackPlayerChange,
}: UseDeckPlayerControllerOptions): UseDeckPlayerControllerResult => {
  const queryClient = useQueryClient();
  const { data: me, isLoading: isMeLoading } = useGetMe();
  const [volume, setVolume] = useState(72);
  const [previewTrack, setPreviewTrack] = useState<PlaylistTrack | null>(null);

  const spotifyMode = useMemo<SpotifyMode>(() => {
    if (isMeLoading || !me) return "loading";
    if (!me.spotifyConnected) return "disconnected";
    if (!me.spotifyPremium) return "non-premium";
    return "ready";
  }, [isMeLoading, me]);

  const {
    state: playerState,
    playTrack,
    pause,
    resume,
    seek,
    setVolume: setSpotifyVolume,
  } = useSpotifyPlayer({ enabled: spotifyMode === "ready" });

  const activeTrackId = useMemo(() => {
    const playlistMatch = tracks.find(
      (track) => track.spotifyUri === playerState.currentTrackUri,
    );
    if (playlistMatch) return playlistMatch.id;

    if (
      previewTrack &&
      previewTrack.spotifyUri === playerState.currentTrackUri
    ) {
      return previewTrack.id;
    }
    return null;
  }, [playerState.currentTrackUri, previewTrack, tracks]);

  const runtimePlaybackBlocked =
    spotifyMode === "ready" &&
    (playerState.status === "premium-required" ||
      playerState.status === "auth-error");
  const showPlaybackControls =
    spotifyMode === "ready" && !runtimePlaybackBlocked;
  const showPremiumRequiredHint =
    spotifyMode === "non-premium" || runtimePlaybackBlocked;

  const playSpotifyUri = useCallback(
    (uri: string) => {
      void playTrack(uri).catch(() => {
        toast.error("Song konnte nicht abgespielt werden.");
      });
    },
    [playTrack],
  );

  const controller = useMemo<DeckPlaylistController | undefined>(() => {
    if (!showPlaybackControls) {
      return undefined;
    }

    return {
      isPlaying: !playerState.isPaused && Boolean(playerState.currentTrackUri),
      activeTrackId,
      positionSeconds: playerState.positionMs / 1000,
      durationSeconds: playerState.durationMs / 1000,
      volume,
      onPlayTrack: (trackId: string) => {
        const track =
          tracks.find((candidate) => candidate.id === trackId) ??
          (previewTrack?.id === trackId ? previewTrack : null);
        if (!track?.spotifyUri) {
          return;
        }

        playSpotifyUri(track.spotifyUri);
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
    };
  }, [
    activeTrackId,
    pause,
    playSpotifyUri,
    playerState.currentTrackUri,
    playerState.durationMs,
    playerState.isPaused,
    playerState.positionMs,
    previewTrack,
    resume,
    seek,
    setSpotifyVolume,
    showPlaybackControls,
    tracks,
    volume,
  ]);

  const previewSpotifyTrack = useCallback(
    (track: SpotifyTrackResponse) => {
      const uri = `spotify:track:${track.id}`;
      setPreviewTrack({
        id: track.id,
        title: track.title,
        artist: track.artist,
        year: track.year?.toString() ?? "",
        durationSeconds: 0,
        coverUrl: track.coverUrl ?? "",
        spotifyUri: uri,
        isPinned: false,
      });
      playSpotifyUri(uri);
    },
    [playSpotifyUri],
  );

  const toggleCurationEventTrackPlayback = useCallback(
    (event: UserCurationEventResponse) => {
      if (!event.trackSpotifyUri) return;

      if (event.trackSpotifyUri === playerState.currentTrackUri) {
        if (playerState.isPaused) {
          void resume();
        } else {
          void pause();
        }
        return;
      }

      const playlistTrack = tracks.find(
        (track) =>
          track.id === event.trackId ||
          track.spotifyUri === event.trackSpotifyUri,
      );

      if (!playlistTrack) {
        setPreviewTrack({
          id: event.trackId,
          title: event.trackTitle,
          artist: event.trackArtist,
          year: event.trackYear?.toString() ?? "",
          durationSeconds: 0,
          coverUrl: event.trackCoverUrl ?? "",
          spotifyUri: event.trackSpotifyUri,
          isPinned: false,
        });
      }

      playSpotifyUri(event.trackSpotifyUri);
    },
    [
      pause,
      playSpotifyUri,
      playerState.currentTrackUri,
      playerState.isPaused,
      resume,
      tracks,
    ],
  );

  useEffect(() => {
    if (!onCurationTrackPlayerChange) return;

    if (!showPlaybackControls) {
      onCurationTrackPlayerChange(null);
      return;
    }

    onCurationTrackPlayerChange({
      activeTrackUri: playerState.currentTrackUri,
      isPlaying: !playerState.isPaused && Boolean(playerState.currentTrackUri),
      onTogglePlayback: toggleCurationEventTrackPlayback,
    });
    return () => onCurationTrackPlayerChange(null);
  }, [
    onCurationTrackPlayerChange,
    playerState.currentTrackUri,
    playerState.isPaused,
    showPlaybackControls,
    toggleCurationEventTrackPlayback,
  ]);

  useEffect(() => {
    if (spotifyMode !== "ready") return;
    if (
      playerState.status !== "premium-required" &&
      playerState.status !== "auth-error"
    ) {
      return;
    }

    void queryClient.invalidateQueries({ queryKey: getGetMeQueryKey() });
  }, [playerState.status, queryClient, spotifyMode]);

  return {
    spotifyMode,
    controller,
    showPlaybackControls,
    showPremiumRequiredHint,
    previewTrack,
    previewSpotifyTrack,
  };
};

import { useCallback, useEffect, useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Download, ListMusic } from "lucide-react";
import { toast } from "sonner";

import type {
  PlaylistTrackResponse,
  SpotifyPlaylistExportResponse,
  SpotifyTrackResponse,
  UserCurationEventResponse,
} from "@/api/generated/model";
import {
  addPlaylistTrack,
  exportSessionPlaylist,
  exportSessionPlaylistToSpotify,
  getGetSessionQueryKey,
  getListSessionsQueryKey,
  pinPlaylistTrack,
  unpinPlaylistTrack,
} from "@/api/generated/session-api";
import { getGetMeQueryKey, useGetMe } from "@/api/generated/user-api";
import { ChatWorkspacePanel } from "@/components/chat/chat-workspace-panel";
import {
  DeckPlaylist,
  type DeckPlaylistController,
} from "@/components/deck/deck-playlist";
import {
  DeckExportActions,
  SpotifyExportResultDialog,
  usePdfPreview,
} from "@/components/deck/export";
import { SpotifyConnectDialog } from "@/components/deck/spotify-connect-dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useSpotifyOAuthPopup } from "@/hooks/useSpotifyOAuthPopup";
import { useSpotifyPlayer } from "@/hooks/useSpotifyPlayer";
import type { PlaylistTrack } from "@/lib/playlist-track";

type DeckWorkspaceViewProps = {
  sessionId: string;
  playlist: {
    name?: string | null;
    tracks: PlaylistTrackResponse[];
    uiRevision?: number;
    uiEvent?: "set" | "track_added" | "track_removed" | "track_replaced";
  };
  onRemoveTrack?: (trackId: string) => Promise<void>;
  onCurationTrackPlayerChange?: (
    bridge: {
      activeTrackUri: string | null;
      isPlaying: boolean;
      onTogglePlayback: (event: UserCurationEventResponse) => void;
    } | null,
  ) => void;
};

type SpotifyMode = "loading" | "disconnected" | "non-premium" | "ready";

export const DeckWorkspaceView = ({
  sessionId,
  playlist,
  onRemoveTrack,
  onCurationTrackPlayerChange,
}: DeckWorkspaceViewProps) => {
  const showSpotifyConnectDialog = false;
  const queryClient = useQueryClient();
  const { data: me, isLoading: isMeLoading } = useGetMe();
  const { isSpotifyOAuthLoading, openSpotifyOAuthPopup } =
    useSpotifyOAuthPopup();
  const [volume, setVolume] = useState(72);
  const [addingSpotifyTrackId, setAddingSpotifyTrackId] = useState<
    string | null
  >(null);
  const [previewTrack, setPreviewTrack] = useState<PlaylistTrack | null>(null);
  const [exportedPlaylist, setExportedPlaylist] =
    useState<SpotifyPlaylistExportResponse | null>(null);
  const [activeTab, setActiveTab] = useState("playlist");
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
        isPinned: track.isPinned,
      })),
    [playlist.tracks],
  );

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

  const previewSpotifyTrack = (track: SpotifyTrackResponse) => {
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
  };

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

  const { pdfPreview, isLoadingPdfPreview } = usePdfPreview({
    sessionId,
    tracks: playlist.tracks,
  });

  const invalidateSessionQueries = async () => {
    if (!sessionId) return;
    await Promise.all([
      queryClient.invalidateQueries({
        queryKey: getGetSessionQueryKey(sessionId),
      }),
      queryClient.invalidateQueries({ queryKey: getListSessionsQueryKey() }),
    ]);
  };

  const addSpotifyTrackMutation = useMutation({
    mutationFn: (track: SpotifyTrackResponse) =>
      addPlaylistTrack(sessionId, {
        title: track.title,
        artist: track.artist,
        year: track.year,
        spotifyUri: `spotify:track:${track.id}`,
        coverUrl: track.coverUrl,
      }),
    onMutate: (track) => {
      setAddingSpotifyTrackId(track.id);
    },
    onSuccess: async () => {
      await invalidateSessionQueries();
    },
    onError: () => {
      toast.error("Song konnte nicht hinzugefügt werden.");
    },
    onSettled: () => {
      setAddingSpotifyTrackId(null);
    },
  });

  const downloadPdfBlob = (blob: Blob) => {
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `prompster-${sessionId}.pdf`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  };

  const downloadPdfMutation = useMutation({
    mutationFn: () => exportSessionPlaylist(sessionId),
    onSuccess: (data) => {
      const blob =
        data instanceof Blob
          ? data
          : new Blob([data as BlobPart], { type: "application/pdf" });
      downloadPdfBlob(blob);
    },
    onError: () => {
      toast.error("PDF konnte nicht heruntergeladen werden.");
    },
  });

  const exportSpotifyMutation = useMutation({
    mutationFn: () => exportSessionPlaylistToSpotify(sessionId),
    onSuccess: (data) => {
      setExportedPlaylist(data);
    },
    onError: () => {
      toast.error("Spotify-Playlist konnte nicht erstellt werden.");
    },
  });

  const toggleTrackPinMutation = useMutation({
    mutationFn: ({
      trackId,
      isPinned,
    }: {
      trackId: string;
      isPinned: boolean;
    }) =>
      isPinned
        ? unpinPlaylistTrack(sessionId, trackId)
        : pinPlaylistTrack(sessionId, trackId),
    onSuccess: async () => {
      await invalidateSessionQueries();
    },
    onError: () => {
      toast.error("Song konnte nicht aktualisiert werden.");
    },
  });

  return (
    <>
      {showSpotifyConnectDialog ? (
        <SpotifyConnectDialog
          open={spotifyMode === "disconnected"}
          onConnect={openSpotifyOAuthPopup}
          isConnecting={isSpotifyOAuthLoading}
        />
      ) : null}

      <ChatWorkspacePanel>
        <Tabs
          defaultValue="playlist"
          onValueChange={setActiveTab}
          className="h-full min-h-0 flex-1 gap-3 overflow-hidden"
        >
          <div className="flex shrink-0 items-center justify-between gap-3">
            <TabsList variant="line" className="h-9">
              <TabsTrigger value="playlist">
                <ListMusic className="size-4" />
                Playlist
              </TabsTrigger>
              <TabsTrigger value="export">
                <Download className="size-4" />
                Export
              </TabsTrigger>
            </TabsList>
            <span className="shrink-0 text-xs font-medium text-muted-foreground">
              {tracks.length} / 50
            </span>
          </div>

          <TabsContent
            value="playlist"
            className="flex min-h-0 flex-1 flex-col overflow-hidden"
          >
            {showPremiumRequiredHint ? (
              <div className="mb-3 rounded-md border border-amber-300/20 bg-amber-500/10 px-3 py-2 text-xs text-amber-100">
                Spotify Premium ist erforderlich fuer In-Browser-Wiedergabe. Du
                kannst die Playlist weiterhin kuratieren und nach Spotify
                exportieren.
              </div>
            ) : null}

            <DeckPlaylist
              initialTracks={tracks}
              playlistUpdate={{
                revision: playlist.uiRevision ?? 0,
                event: playlist.uiEvent,
              }}
              showHeader={false}
              allowLocalRemoval={false}
              onRemoveTrack={onRemoveTrack}
              onAddSpotifyTrack={async (track) => {
                await addSpotifyTrackMutation.mutateAsync(track);
              }}
              onToggleTrackPin={async (trackId, isPinned) => {
                await toggleTrackPinMutation.mutateAsync({
                  trackId,
                  isPinned,
                });
              }}
              onPreviewSpotifyTrack={
                showPlaybackControls ? previewSpotifyTrack : undefined
              }
              previewTrack={previewTrack}
              isAddingSpotifyTrack={addSpotifyTrackMutation.isPending}
              pinningTrackId={
                toggleTrackPinMutation.isPending
                  ? toggleTrackPinMutation.variables?.trackId
                  : null
              }
              addingSpotifyTrackId={addingSpotifyTrackId}
              controller={controller}
            />
          </TabsContent>

          <TabsContent
            value="export"
            className="flex min-h-0 flex-1 flex-col overflow-hidden"
          >
            <DeckExportActions
              trackCount={tracks.length}
              pdfPreview={pdfPreview}
              isActive={activeTab === "export"}
              isLoadingPdfPreview={isLoadingPdfPreview}
              isDownloadingPdf={downloadPdfMutation.isPending}
              isExportingSpotify={exportSpotifyMutation.isPending}
              onDownloadPdf={() => downloadPdfMutation.mutate()}
              onExportSpotify={() => exportSpotifyMutation.mutate()}
            />
          </TabsContent>
        </Tabs>
      </ChatWorkspacePanel>

      <SpotifyExportResultDialog
        playlist={exportedPlaylist}
        tracks={tracks}
        onOpenChange={(open) => {
          if (!open) setExportedPlaylist(null);
        }}
      />
    </>
  );
};

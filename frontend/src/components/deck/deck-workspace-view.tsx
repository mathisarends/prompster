import { useEffect, useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Download,
  ExternalLink,
  FileText,
  ListMusic,
  Loader2,
  Music2,
  RefreshCw,
} from "lucide-react";
import { toast } from "sonner";

import type {
  PlaylistTrackResponse,
  SpotifyPlaylistExportResponse,
  SpotifyTrackResponse,
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
import { useGetMe } from "@/api/generated/user-api";
import { ChatWorkspacePanel } from "@/components/chat/chat-workspace-panel";
import {
  DeckPlaylist,
  type DeckPlaylistController,
} from "@/components/deck/deck-playlist";
import { SpotifyConnectDialog } from "@/components/deck/spotify-connect-dialog";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useSpotifyOAuthPopup } from "@/hooks/useSpotifyOAuthPopup";
import { useSpotifyPlayer } from "@/hooks/useSpotifyPlayer";

type DeckWorkspaceViewProps = {
  sessionId: string;
  playlist: {
    name?: string | null;
    tracks: PlaylistTrackResponse[];
  };
  onRemoveTrack?: (trackId: string) => Promise<void>;
};

export const DeckWorkspaceView = ({
  sessionId,
  playlist,
  onRemoveTrack,
}: DeckWorkspaceViewProps) => {
  const queryClient = useQueryClient();
  const { data: me, isLoading: isMeLoading } = useGetMe();
  const { isSpotifyOAuthLoading, openSpotifyOAuthPopup } =
    useSpotifyOAuthPopup();
  const [volume, setVolume] = useState(72);
  const [addingSpotifyTrackId, setAddingSpotifyTrackId] = useState<
    string | null
  >(null);
  const [exportedPlaylist, setExportedPlaylist] =
    useState<SpotifyPlaylistExportResponse | null>(null);
  const [pdfPreview, setPdfPreview] = useState<{
    url: string;
    blob: Blob;
  } | null>(null);
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
        isPinned: track.isPinned,
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

  const exportPdfMutation = useMutation({
    mutationFn: () => exportSessionPlaylist(sessionId),
    onSuccess: (data) => {
      const blob =
        data instanceof Blob
          ? data
          : new Blob([data as BlobPart], { type: "application/pdf" });
      const url = window.URL.createObjectURL(blob);
      setPdfPreview((currentPreview) => {
        if (currentPreview) {
          window.URL.revokeObjectURL(currentPreview.url);
        }

        return { url, blob };
      });
    },
    onError: () => {
      toast.error("PDF-Vorschau konnte nicht erstellt werden.");
    },
  });

  useEffect(() => {
    setPdfPreview((currentPreview) => {
      if (currentPreview) {
        window.URL.revokeObjectURL(currentPreview.url);
      }

      return null;
    });
  }, [sessionId, playlist.tracks]);

  useEffect(
    () => () => {
      if (pdfPreview) {
        window.URL.revokeObjectURL(pdfPreview.url);
      }
    },
    [pdfPreview],
  );

  const downloadPdfPreview = () => {
    if (!pdfPreview) return;

    const link = document.createElement("a");
    link.href = pdfPreview.url;
    link.download = `prompster-${sessionId}.pdf`;
    document.body.appendChild(link);
    link.click();
    link.remove();
  };

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
    onSuccess: async (_data, variables) => {
      await invalidateSessionQueries();
      toast.success(
        variables.isPinned ? "Song wurde entpinnt." : "Song wurde angepinnt.",
      );
    },
    onError: () => {
      toast.error("Song konnte nicht aktualisiert werden.");
    },
  });

  return (
    <>
      <SpotifyConnectDialog
        open={connectRequired}
        onConnect={openSpotifyOAuthPopup}
        isConnecting={isSpotifyOAuthLoading}
      />

      <ChatWorkspacePanel>
        <Tabs
          defaultValue="playlist"
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
              onAddSpotifyTrack={async (track) => {
                await addSpotifyTrackMutation.mutateAsync(track);
              }}
              onToggleTrackPin={async (trackId, isPinned) => {
                await toggleTrackPinMutation.mutateAsync({
                  trackId,
                  isPinned,
                });
              }}
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
            <ExportActions
              trackCount={tracks.length}
              pdfPreview={pdfPreview}
              isExportingPdf={exportPdfMutation.isPending}
              isExportingSpotify={exportSpotifyMutation.isPending}
              onLoadPdfPreview={() => exportPdfMutation.mutate()}
              onDownloadPdf={downloadPdfPreview}
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

type ExportActionsProps = {
  trackCount: number;
  pdfPreview: {
    url: string;
    blob: Blob;
  } | null;
  isExportingPdf: boolean;
  isExportingSpotify: boolean;
  onLoadPdfPreview: () => void;
  onDownloadPdf: () => void;
  onExportSpotify: () => void;
};

const ExportActions = ({
  trackCount,
  pdfPreview,
  isExportingPdf,
  isExportingSpotify,
  onLoadPdfPreview,
  onDownloadPdf,
  onExportSpotify,
}: ExportActionsProps) => {
  const disabled = trackCount === 0;

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden pt-1">
      <div className="min-h-0 flex-1 overflow-hidden rounded-md border border-white/[0.08] bg-white/[0.025]">
        {pdfPreview ? (
          <iframe
            src={pdfPreview.url}
            title="PDF-Vorschau"
            className="h-full min-h-[360px] w-full bg-white"
          />
        ) : (
          <div className="grid h-full min-h-[360px] place-items-center px-6 text-center">
            <div className="max-w-xs">
              <div className="mx-auto grid size-14 place-items-center rounded-md bg-primary/12 text-primary">
                {isExportingPdf ? (
                  <Loader2 className="size-6 animate-spin" />
                ) : (
                  <FileText className="size-6" />
                )}
              </div>
              <p className="mt-4 text-sm font-semibold">
                PDF-Vorschau noch nicht erstellt
              </p>
              <p className="mt-1 text-xs leading-5 text-muted-foreground">
                Erzeuge zuerst die Vorschau, dann kannst du genau diese Datei
                herunterladen.
              </p>
            </div>
          </div>
        )}
      </div>

      {disabled ? (
        <p className="px-1 py-3 text-xs text-muted-foreground">
          Füge mindestens einen Song hinzu, um die Liste zu exportieren.
        </p>
      ) : null}

      <div className="deck-export-bar -mx-5 -mb-5 mt-3 shrink-0 border-t border-white/[0.08] bg-background/78 px-5 pb-3 pt-4 shadow-[0_-18px_46px_hsl(222_52%_4%/0.36)] backdrop-blur-xl">
        <div className="flex min-h-16 items-center gap-3 px-1.5">
          <div className="grid size-12 shrink-0 place-items-center rounded-[4px] bg-white/[0.06] text-primary shadow-[0_10px_28px_hsl(0_0%_0%/0.28)] ring-1 ring-white/[0.06]">
            <FileText className="size-5" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold leading-tight text-foreground">
              Karten-PDF
            </p>
            <p className="mt-0.5 truncate text-xs text-muted-foreground">
              {pdfPreview
                ? `${formatFileSize(pdfPreview.blob.size)} bereit zur Prüfung`
                : `${trackCount} Songs als druckbares Deck`}
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <Button
              type="button"
              variant="outline"
              size="icon"
              aria-label={
                pdfPreview ? "PDF-Vorschau erneuern" : "PDF-Vorschau erstellen"
              }
              disabled={disabled || isExportingPdf || isExportingSpotify}
              onClick={onLoadPdfPreview}
            >
              {isExportingPdf ? (
                <Loader2 className="size-4 animate-spin" />
              ) : pdfPreview ? (
                <RefreshCw className="size-4" />
              ) : (
                <FileText className="size-4" />
              )}
            </Button>
            <Button
              type="button"
              variant="outline"
              size="icon"
              aria-label="PDF herunterladen"
              disabled={!pdfPreview || disabled || isExportingPdf}
              onClick={onDownloadPdf}
            >
              <Download className="size-4" />
            </Button>
            <Button
              type="button"
              variant="outline"
              size="icon"
              aria-label="Spotify-Playlist erstellen"
              disabled={disabled || isExportingPdf || isExportingSpotify}
              onClick={onExportSpotify}
            >
              {isExportingSpotify ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <Music2 className="size-4" />
              )}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

const formatFileSize = (bytes: number) => {
  if (bytes < 1024 * 1024) {
    return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  }

  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
};

type SpotifyExportResultDialogProps = {
  playlist: SpotifyPlaylistExportResponse | null;
  tracks: Array<{
    title: string;
    coverUrl: string;
  }>;
  onOpenChange: (open: boolean) => void;
};

const SpotifyExportResultDialog = ({
  playlist,
  tracks,
  onOpenChange,
}: SpotifyExportResultDialogProps) => {
  const covers = tracks.filter((track) => track.coverUrl).slice(0, 4);

  return (
    <Dialog open={Boolean(playlist)} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md overflow-hidden rounded-lg">
        <div className="flex gap-4 p-4">
          <div className="grid size-28 shrink-0 grid-cols-2 overflow-hidden rounded-md bg-white/[0.06]">
            {covers.length > 0 ? (
              covers.map((track) => (
                <img
                  key={`${track.title}-${track.coverUrl}`}
                  src={track.coverUrl}
                  alt={`${track.title} Cover`}
                  className="h-full w-full object-cover"
                />
              ))
            ) : (
              <div className="col-span-2 grid h-full place-items-center text-muted-foreground">
                <Music2 className="size-8" />
              </div>
            )}
          </div>
          <div className="min-w-0 flex-1 pt-1">
            <DialogTitle>Spotify-Playlist bereit</DialogTitle>
            <DialogDescription className="mt-1">
              {playlist?.trackCount ?? 0} Songs wurden exportiert.
            </DialogDescription>
            <p className="mt-4 truncate text-sm font-semibold">
              {playlist?.name}
            </p>
            <p className="mt-1 truncate text-xs text-muted-foreground">
              {playlist?.url}
            </p>
            <Button
              type="button"
              size="sm"
              className="mt-4"
              onClick={() => {
                if (playlist?.url)
                  window.open(playlist.url, "_blank", "noopener");
              }}
            >
              <ExternalLink className="size-4" />
              Öffnen
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};

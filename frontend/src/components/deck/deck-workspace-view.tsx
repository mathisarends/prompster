import { useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Download,
  ExternalLink,
  FileText,
  ListMusic,
  Loader2,
  Music2,
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
import { cn } from "@/lib/utils";

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
      const link = document.createElement("a");
      link.href = url;
      link.download = `prompster-${sessionId}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    },
    onError: () => {
      toast.error("PDF konnte nicht exportiert werden.");
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
              isExportingPdf={exportPdfMutation.isPending}
              isExportingSpotify={exportSpotifyMutation.isPending}
              onExportPdf={() => exportPdfMutation.mutate()}
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
  isExportingPdf: boolean;
  isExportingSpotify: boolean;
  onExportPdf: () => void;
  onExportSpotify: () => void;
};

const ExportActions = ({
  trackCount,
  isExportingPdf,
  isExportingSpotify,
  onExportPdf,
  onExportSpotify,
}: ExportActionsProps) => {
  const disabled = trackCount === 0;

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3 pt-1">
      <ExportActionButton
        icon={FileText}
        title="PDF exportieren"
        description="Deck als druckbare Playlist-Datei herunterladen."
        isLoading={isExportingPdf}
        disabled={disabled || isExportingPdf || isExportingSpotify}
        onClick={onExportPdf}
      />
      <ExportActionButton
        icon={Music2}
        title="Spotify-Playlist erstellen"
        description="Liste in Spotify anlegen oder aktualisieren."
        isLoading={isExportingSpotify}
        disabled={disabled || isExportingPdf || isExportingSpotify}
        onClick={onExportSpotify}
      />
      {disabled ? (
        <p className="px-1 text-xs text-muted-foreground">
          Füge mindestens einen Song hinzu, um die Liste zu exportieren.
        </p>
      ) : null}
    </div>
  );
};

type ExportActionButtonProps = {
  icon: typeof FileText;
  title: string;
  description: string;
  isLoading: boolean;
  disabled: boolean;
  onClick: () => void;
};

const ExportActionButton = ({
  icon: Icon,
  title,
  description,
  isLoading,
  disabled,
  onClick,
}: ExportActionButtonProps) => (
  <button
    type="button"
    disabled={disabled}
    onClick={onClick}
    className={cn(
      "grid w-full grid-cols-[44px_minmax(0,1fr)_auto] items-center gap-3 rounded-md border border-white/[0.08] bg-white/[0.03] px-3 py-3 text-left transition-colors hover:bg-white/[0.06] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/60 disabled:cursor-not-allowed disabled:opacity-50",
    )}
  >
    <span className="grid size-11 place-items-center rounded-md bg-primary/12 text-primary">
      <Icon className="size-5" />
    </span>
    <span className="min-w-0">
      <span className="block truncate text-sm font-semibold">{title}</span>
      <span className="mt-0.5 block truncate text-xs text-muted-foreground">
        {description}
      </span>
    </span>
    {isLoading ? (
      <Loader2 className="size-4 animate-spin text-muted-foreground" />
    ) : (
      <ExternalLink className="size-4 text-muted-foreground" />
    )}
  </button>
);

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

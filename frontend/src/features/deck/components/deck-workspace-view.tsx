import { useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Download, ListMusic } from "lucide-react";
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
} from "@/api/generated/session-api";
import { ChatWorkspacePanel } from "@/shared/components/workspace-panel-shell";
import { DeckPlaylist } from "@/features/deck/components/deck-playlist";
import {
  DeckExportActions,
  SpotifyExportResultDialog,
  usePdfPreview,
} from "@/features/deck/components/export";
import { SpotifyConnectDialog } from "@/features/spotify/components/spotify-connect-dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/shared/ui/tabs";
import {
  type CurationTrackPlayerBridge,
  useDeckPlayerController,
} from "@/features/deck/hooks/useDeckPlayerController";
import { useSpotifyOAuthPopup } from "@/features/spotify/hooks/useSpotifyOAuthPopup";

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
    bridge: CurationTrackPlayerBridge | null,
  ) => void;
};

export const DeckWorkspaceView = ({
  sessionId,
  playlist,
  onRemoveTrack,
  onCurationTrackPlayerChange,
}: DeckWorkspaceViewProps) => {
  const showSpotifyConnectDialog = false;
  const queryClient = useQueryClient();
  const { isSpotifyOAuthLoading, openSpotifyOAuthPopup } =
    useSpotifyOAuthPopup();
  const [addingSpotifyTrackId, setAddingSpotifyTrackId] = useState<
    string | null
  >(null);
  const [exportedPlaylist, setExportedPlaylist] =
    useState<SpotifyPlaylistExportResponse | null>(null);
  const [activeTab, setActiveTab] = useState("playlist");

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

  const {
    spotifyMode,
    controller,
    showPlaybackControls,
    showPremiumRequiredHint,
    previewTrack,
    previewSpotifyTrack,
  } = useDeckPlayerController({
    tracks,
    onCurationTrackPlayerChange,
  });

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

  return (
    <>
      {showSpotifyConnectDialog ? (
        <SpotifyConnectDialog
          open={spotifyMode === "disconnected"}
          onConnect={openSpotifyOAuthPopup}
          isConnecting={isSpotifyOAuthLoading}
        />
      ) : null}

      <ChatWorkspacePanel contentClassName="px-0 pb-0">
        <Tabs
          defaultValue="playlist"
          onValueChange={setActiveTab}
          className="h-full min-h-0 flex-1 gap-3 overflow-hidden"
        >
          <div className="flex shrink-0 items-center justify-between gap-3 px-5">
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
              <div className="mx-5 mb-3 rounded-md border border-amber-300/20 bg-amber-500/10 px-3 py-2 text-xs text-amber-100">
                Spotify Premium ist erforderlich für In-Browser-Wiedergabe. Du
                kannst die Playlist weiterhin kuratieren und nach Spotify
                exportieren.
              </div>
            ) : null}

            <DeckPlaylist
              className="px-5"
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
              onPreviewSpotifyTrack={
                showPlaybackControls ? previewSpotifyTrack : undefined
              }
              previewTrack={previewTrack}
              isAddingSpotifyTrack={addSpotifyTrackMutation.isPending}
              addingSpotifyTrackId={addingSpotifyTrackId}
              controller={controller}
            />
          </TabsContent>

          <TabsContent
            value="export"
            className="flex min-h-0 flex-1 flex-col overflow-hidden px-5 pb-5"
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

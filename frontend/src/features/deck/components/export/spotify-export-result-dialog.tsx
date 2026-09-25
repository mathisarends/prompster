import { Music2 } from "lucide-react";

import type { SpotifyPlaylistExportResponse } from "@/api/session-rpc";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "@/shared/ui/dialog";

import { OpenSpotifyPlaylistButton } from "./open-spotify-playlist-button";

export type SpotifyExportResultTrack = {
  title: string;
  coverUrl?: string | null;
};

type SpotifyExportResultDialogProps = {
  playlist: SpotifyPlaylistExportResponse | null;
  tracks: SpotifyExportResultTrack[];
  onOpenChange: (open: boolean) => void;
};

export const SpotifyExportResultDialog = ({
  playlist,
  tracks,
  onOpenChange,
}: SpotifyExportResultDialogProps) => {
  const covers = tracks.filter((track) => track.coverUrl).slice(0, 4);

  return (
    <Dialog open={Boolean(playlist)} onOpenChange={onOpenChange}>
      <DialogContent className="w-[calc(100%-2rem)] max-w-lg overflow-hidden rounded-lg border-emerald-400/20 bg-sidebar p-0 shadow-[0_24px_80px_hsl(150_50%_4%/0.55)]">
        <div className="border-b border-emerald-300/15 bg-[linear-gradient(135deg,hsl(152_76%_20%/0.28),transparent_58%)] px-5 py-4">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase text-emerald-200/85">
            <span className="size-2 rounded-full bg-emerald-400 shadow-[0_0_18px_hsl(142_76%_46%/0.8)]" />
            Export abgeschlossen
          </div>
        </div>

        <div className="grid gap-5 p-5 sm:grid-cols-[8.5rem_minmax(0,1fr)] sm:items-center">
          <PlaylistCoverMosaic covers={covers} />
          <SpotifyExportSummary playlist={playlist} />
        </div>
      </DialogContent>
    </Dialog>
  );
};

type PlaylistCoverMosaicProps = {
  covers: SpotifyExportResultTrack[];
};

const PlaylistCoverMosaic = ({ covers }: PlaylistCoverMosaicProps) => (
  <div className="relative mx-auto size-32 shrink-0 sm:mx-0">
    <div className="absolute -inset-2 rounded-lg border border-emerald-300/15 bg-emerald-400/5 blur-sm" />
    <div className="relative grid size-32 grid-cols-2 overflow-hidden rounded-md bg-white/[0.06] shadow-2xl ring-1 ring-white/10">
      {covers.length > 0 ? (
        covers.map((track) => (
          <img
            key={`${track.title}-${track.coverUrl}`}
            src={track.coverUrl ?? undefined}
            alt={`${track.title} Cover`}
            className="h-full w-full object-cover"
          />
        ))
      ) : (
        <div className="col-span-2 grid h-full place-items-center text-muted-foreground">
          <Music2 className="size-9" />
        </div>
      )}
    </div>
  </div>
);

type SpotifyExportSummaryProps = {
  playlist: SpotifyPlaylistExportResponse | null;
};

const SpotifyExportSummary = ({ playlist }: SpotifyExportSummaryProps) => (
  <div className="min-w-0 text-center sm:text-left">
    <DialogTitle className="text-lg leading-tight text-foreground">
      Spotify-Playlist bereit
    </DialogTitle>
    <DialogDescription className="mt-1 text-sm">
      {playlist?.trackCount ?? 0} Songs wurden exportiert.
    </DialogDescription>

    <div className="mt-5 flex min-w-0 flex-col gap-3 border-l border-emerald-300/25 pl-3 sm:flex-row sm:items-center">
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-semibold text-foreground">
          {playlist?.name ?? "Spotify-Playlist"}
        </p>
        <p className="mt-1 truncate text-xs text-muted-foreground">
          {playlist?.url}
        </p>
      </div>
      <OpenSpotifyPlaylistButton
        url={playlist?.url}
        className="w-full sm:w-auto"
      />
    </div>
  </div>
);

import { useMemo } from "react";
import { ListMusic } from "lucide-react";

import type { PlaylistTrackResponse } from "@/api/generated/model";
import { ChatWorkspacePanel } from "@/components/chat/chat-workspace-panel";
import { DeckPlaylist } from "@/components/deck/deck-playlist";

type DeckWorkspaceViewProps = {
  playlist: {
    name?: string | null;
    tracks: PlaylistTrackResponse[];
  };
};

export const DeckWorkspaceView = ({ playlist }: DeckWorkspaceViewProps) => {
  const tracks = useMemo(
    () =>
      playlist.tracks.map((track) => ({
        id: track.id,
        title: track.title,
        artist: track.artist,
        year: track.year?.toString() ?? "",
        durationSeconds: 0,
        coverUrl: track.coverUrl ?? "",
      })),
    [playlist.tracks],
  );

  return (
    <ChatWorkspacePanel
      header={
        <div className="flex items-center gap-1.5 px-1.5 py-2 text-sm font-semibold">
          <ListMusic className="size-4" />
          Liste
        </div>
      }
    >
      <div className="flex min-h-0 flex-1 flex-col pt-2">
        <DeckPlaylist
          initialTracks={tracks}
          showHeader={false}
          allowLocalRemoval={false}
        />
      </div>
    </ChatWorkspacePanel>
  );
};

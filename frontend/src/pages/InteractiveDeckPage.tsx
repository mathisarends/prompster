import { useState } from "react";
import { useLocation } from "react-router-dom";
import { MultiResizableGrid } from "../components/MultiResizableGrid";
import { DeckViewTabs, type DeckViewMode } from "../components/DeckViewTabs";
import { TrackPlaylist } from "../components/TrackPlaylist";
import { ChatSidebar } from "../components/interactiveDeck/ChatSidebar";
import { CardPlaceholderGrid } from "../components/interactiveDeck/CardPlaceholderGrid";
import { DeckFooter } from "../components/interactiveDeck/DeckFooter";
import { mockTracks } from "../components/interactiveDeck/mockTracks";

type LocationState = {
  prompt?: string;
};

export const InteractiveDeckPage = () => {
  const location = useLocation();
  const state = (location.state as LocationState | null) ?? null;
  const [activeView, setActiveView] = useState<DeckViewMode>("playlist");

  const rightPanel = (
    <section className="flex h-full min-h-0 flex-col bg-[var(--beatline-surface)]/45">
      <DeckViewTabs
        activeView={activeView}
        onChange={setActiveView}
        visibleSongs={mockTracks.length}
        totalSongs={50}
      />

      {activeView === "playlist" ? (
        <TrackPlaylist initialTracks={mockTracks} />
      ) : (
        <CardPlaceholderGrid />
      )}

      <DeckFooter />
    </section>
  );

  return (
    <div className="h-screen bg-[radial-gradient(circle_at_top,_#2D2D44_0%,_#1A1A2E_45%,_#16213E_100%)] text-[var(--beatline-text)]">
      <MultiResizableGrid
        left={<ChatSidebar initialPrompt={state?.prompt} />}
        right={rightPanel}
        initialLeftWidth={320}
        minLeftWidth={260}
        maxLeftWidth={540}
      />
    </div>
  );
};

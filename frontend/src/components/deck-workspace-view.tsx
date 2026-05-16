import { useState } from "react";
import { LayoutGrid, ListMusic } from "lucide-react";

import { Card } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ChatWorkspacePanel } from "@/components/chat-workspace-panel";
import { DeckPlaylist } from "@/components/deck-playlist";

type DeckWorkspaceViewProps = {
  onClose: () => void;
};

type DeckViewMode = "playlist" | "cards";

export const DeckWorkspaceView = ({ onClose }: DeckWorkspaceViewProps) => {
  const [activeView, setActiveView] = useState<DeckViewMode>("playlist");

  return (
    <Tabs
      value={activeView}
      onValueChange={(value) => setActiveView(value as DeckViewMode)}
      className="flex h-full min-h-0 flex-col"
    >
      <ChatWorkspacePanel
        onClose={onClose}
        header={
          <TabsList variant="line" className="h-auto p-0">
            <TabsTrigger
              value="playlist"
              className="gap-1.5 rounded-none px-1.5 py-2 text-sm font-semibold"
            >
              <ListMusic className="size-4" />
              Liste
            </TabsTrigger>
            <TabsTrigger
              value="cards"
              className="gap-1.5 rounded-none px-1.5 py-2 text-sm font-semibold"
            >
              <LayoutGrid className="size-4" />
              Karten
            </TabsTrigger>
          </TabsList>
        }
      >
        <TabsContent
          value="playlist"
          className="flex min-h-0 flex-1 flex-col pt-2 data-[hidden]:hidden"
        >
          <DeckPlaylist showHeader={false} />
        </TabsContent>

        <TabsContent
          value="cards"
          className="min-h-0 flex-1 data-[hidden]:hidden"
        >
          <ScrollArea className="h-full pr-2">
            <div className="grid grid-cols-2 gap-3 pb-3 sm:grid-cols-3">
              {Array.from({ length: 6 }).map((_, idx) => (
                <Card
                  key={`card-placeholder-${idx}`}
                  size="sm"
                  className="gap-3 border-0 bg-white/[0.035] p-3 shadow-none"
                >
                  <div className="h-24 rounded-md bg-white/[0.045]" />
                  <div>
                    <p className="text-sm font-semibold">
                      Kartenansicht Platzhalter
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Hier kommen deine Deck-Karten hin.
                    </p>
                  </div>
                </Card>
              ))}
            </div>
          </ScrollArea>
        </TabsContent>
      </ChatWorkspacePanel>
    </Tabs>
  );
};

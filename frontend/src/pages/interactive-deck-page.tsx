import { useState } from "react";
import { useLocation } from "react-router-dom";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import {
  LayoutGrid,
  ListMusic,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { DeckPlaylist } from "@/components/deck-playlist";
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ChatInputBox } from "@/components/chat-input-box";
import { cn } from "@/lib/utils";
import { mockTracks } from "@/lib/mockTracks";
import { useLocalStorage } from "@/hooks/useLocalStorage";

type LocationState = {
  prompt?: string;
};

type DeckViewMode = "playlist" | "cards";
type ChatRole = "assistant" | "user";

type ChatMessage = {
  id: string;
  role: ChatRole;
  text: string;
};

export const InteractiveDeckPage = () => {
  const location = useLocation();
  const state = (location.state as LocationState | null) ?? null;

  useDocumentTitle(state?.prompt?.trim() ?? "Deck");

  const [activeView, setActiveView] = useState<DeckViewMode>("playlist");
  const [visibleTrackCount, setVisibleTrackCount] = useState(mockTracks.length);
  const [chatInput, setChatInput] = useState("");
  const [panelLayout, setPanelLayout] = useLocalStorage<Record<string, number>>(
    "prompster.deck.panel-layout",
    { chat: 50, deck: 50 },
  );

  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    const seedPrompt =
      state?.prompt?.trim() ?? "Lass uns ein 80er/90er Pop Deck bauen.";

    return [
      {
        id: "assistant-1",
        role: "assistant",
        text: "Top, ich erstelle mit dir jetzt Schritt fur Schritt ein Deck.",
      },
      { id: "user-1", role: "user", text: seedPrompt },
      {
        id: "assistant-2",
        role: "assistant",
        text: "Fokus verstanden. Ich schlage jetzt passende Songs in der Liste vor.",
      },
    ];
  });

  const sendChatMessage = (text: string) => {
    setMessages((prev) => [
      ...prev,
      {
        id: `user-${crypto.randomUUID()}`,
        role: "user",
        text,
      },
      {
        id: `assistant-${crypto.randomUUID()}`,
        role: "assistant",
        text: "Verstanden. Ich aktualisiere jetzt die Vorschlage fur dein Deck.",
      },
    ]);
  };

  const renderMessageBubble = (message: ChatMessage) => (
    <div
      key={message.id}
      className={cn(
        "text-sm leading-relaxed",
        message.role === "user"
          ? "ml-auto max-w-[86%] rounded-2xl bg-white/10 px-4 py-3 text-foreground"
          : "max-w-[92%] px-1 py-1.5 text-muted-foreground",
      )}
    >
      {message.text}
    </div>
  );

  const rightPanel = (
    <Card className="h-full rounded-none border-0 bg-[hsl(222_36%_7%)] py-0 shadow-none ring-0 md:rounded-none">
      <div className="flex h-full min-h-0 flex-col">
        <div className="flex min-h-0 flex-1 flex-col px-4 py-4 sm:px-5 sm:py-5">
          <Tabs
            value={activeView}
            onValueChange={(value) => setActiveView(value as DeckViewMode)}
            className="flex min-h-0 flex-1 flex-col"
          >
            <div className="flex items-center justify-between gap-3">
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
              <Badge
                variant="outline"
                className="h-7 rounded-full border-transparent bg-white/[0.045] px-2.5 text-[11px] uppercase tracking-[0.1em] text-muted-foreground"
              >
                {visibleTrackCount} / 50 Songs
              </Badge>
            </div>

            <TabsContent
              value="playlist"
              className="mt-3 flex min-h-0 flex-1 flex-col"
            >
              <DeckPlaylist
                onVisibleTrackCountChange={setVisibleTrackCount}
                showHeader={false}
              />
            </TabsContent>

            <TabsContent value="cards" className="mt-3 min-h-0 flex-1">
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
          </Tabs>
        </div>
      </div>
    </Card>
  );

  const leftPanel = (
    <Card className="h-full rounded-none border-0 bg-[hsl(222_36%_7%)] py-0 shadow-none ring-0">
      <aside className="flex h-full min-h-0 flex-col">
        <div className="flex items-center justify-between px-4 py-4 sm:px-5 sm:py-5"></div>

        <ScrollArea className="min-h-0 flex-1 px-4 pb-4 sm:px-5 sm:pb-5">
          <div className="space-y-4 pr-1">
            {messages.map(renderMessageBubble)}
          </div>
        </ScrollArea>

        <div className="px-4 pb-4 pt-3 sm:px-5 sm:pb-5">
          <ChatInputBox
            value={chatInput}
            onChange={setChatInput}
            onSubmit={sendChatMessage}
            placeholder="Antworte oder stell eine Frage"
            className="rounded-3xl border-transparent bg-[hsl(222_30%_10%)] p-4 shadow-none"
            textareaClassName="max-h-40"
            rows={1}
          />
        </div>
      </aside>
    </Card>
  );

  return (
    <div className="h-dvh overflow-hidden bg-[linear-gradient(165deg,_hsl(222_42%_8%)_0%,_hsl(222_48%_5%)_100%)] text-foreground">
      <div className="mx-auto h-full w-full p-0">
        <div className="flex h-full min-h-0 flex-col md:hidden">
          <div className="h-[52dvh] min-h-[300px]">{leftPanel}</div>
          <div className="min-h-0 flex-1">{rightPanel}</div>
        </div>

        <div className="hidden h-full min-h-0 md:block">
          <ResizablePanelGroup
            orientation="horizontal"
            className="h-full bg-transparent"
            defaultLayout={panelLayout}
            onLayoutChanged={setPanelLayout}
          >
            <ResizablePanel
              id="chat"
              defaultSize={`${panelLayout.chat ?? 50}`}
              minSize="32"
              maxSize="68"
            >
              {leftPanel}
            </ResizablePanel>
            <ResizableHandle
              withHandle
              className="w-px cursor-col-resize bg-white/5 hover:bg-white/10 data-[separator=active]:bg-primary/35"
            />
            <ResizablePanel
              id="deck"
              defaultSize={`${panelLayout.deck ?? 50}`}
              minSize="32"
              maxSize="68"
            >
              {rightPanel}
            </ResizablePanel>
          </ResizablePanelGroup>
        </div>
      </div>
    </div>
  );
};

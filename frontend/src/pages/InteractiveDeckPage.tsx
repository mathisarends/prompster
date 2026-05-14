import { useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  ArrowUp,
  LayoutGrid,
  ListMusic,
  Play,
  Search,
  Sparkles,
  X,
} from "lucide-react";

import { PrompsterLogo } from "@/components/prompster-logo";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ChatInputBox } from "@/components/chat-input-box";
import { cn } from "@/lib/utils";
import { mockTracks, type PlaylistTrack } from "@/lib/mockTracks";

type LocationState = {
  prompt?: string;
  attachments?: Array<{
    name: string;
    size: number;
    type?: string;
    previewUrl?: string;
  }>;
};

type DeckViewMode = "playlist" | "cards";
type ChatRole = "assistant" | "user";

type ChatMessage = {
  id: string;
  role: ChatRole;
  text: string;
};

export const InteractiveDeckPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const state = (location.state as LocationState | null) ?? null;
  const [activeView, setActiveView] = useState<DeckViewMode>("playlist");
  const [tracks, setTracks] = useState(mockTracks);
  const [query, setQuery] = useState("");
  const [chatInput, setChatInput] = useState("");

  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    const seedAttachments = state?.attachments ?? [];
    const trimmedPrompt = state?.prompt?.trim();
    const seedPrompt =
      trimmedPrompt ||
      (seedAttachments.length > 0
        ? "Datei(en) angehangt"
        : "Lass uns ein 80er/90er Pop Deck bauen.");
    const attachmentSuffix =
      seedAttachments.length > 0
        ? ` [${seedAttachments.length} Datei(en): ${seedAttachments
            .map((file) => file.name)
            .join(", ")}]`
        : "";

    return [
      {
        id: "assistant-1",
        role: "assistant",
        text: "Top, ich erstelle mit dir jetzt Schritt fur Schritt ein Deck.",
      },
      { id: "user-1", role: "user", text: `${seedPrompt}${attachmentSuffix}` },
      {
        id: "assistant-2",
        role: "assistant",
        text: "Fokus verstanden. Ich schlage jetzt passende Songs in der Liste vor.",
      },
    ];
  });

  const filteredTracks = useMemo(() => {
    const normalized = query.trim().toLowerCase();

    if (!normalized) {
      return tracks;
    }

    return tracks.filter((track) =>
      `${track.title} ${track.artist} ${track.year} ${track.genre}`
        .toLowerCase()
        .includes(normalized),
    );
  }, [query, tracks]);

  const removeTrack = (trackId: string) => {
    setTracks((prev) => prev.filter((track) => track.id !== trackId));
  };

  const sendChatMessage = (
    text: string,
    attachments: Array<{ name: string }>,
  ) => {
    const attachmentSuffix =
      attachments.length > 0
        ? ` [${attachments.length} Datei(en): ${attachments.map((f) => f.name).join(", ")}]`
        : "";

    setMessages((prev) => [
      ...prev,
      {
        id: `user-${crypto.randomUUID()}`,
        role: "user",
        text: `${text || "Datei gesendet"}${attachmentSuffix}`,
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
        "max-w-[92%] rounded-lg border px-3 py-2 text-sm leading-relaxed",
        message.role === "user"
          ? "ml-auto border-primary/40 bg-primary/15 text-foreground"
          : "border-border/70 bg-background/80 text-muted-foreground",
      )}
    >
      {message.text}
    </div>
  );

  const renderTrackRow = (track: PlaylistTrack, index: number) => (
    <div
      key={track.id}
      className={cn(
        "group grid grid-cols-[52px_minmax(0,1fr)_70px_95px_44px] items-center rounded-md border border-transparent px-3 py-2 transition-colors",
        index === 0 ? "bg-muted/70" : "hover:bg-muted/45",
      )}
    >
      <div className="relative grid place-items-center text-sm tabular-nums text-muted-foreground">
        <span className="group-hover:hidden">{index + 1}</span>
        <Button
          size="icon-xs"
          variant="ghost"
          className="absolute hidden group-hover:inline-flex"
          aria-label={`${track.title} abspielen`}
        >
          <Play className="size-3.5 fill-current" />
        </Button>
      </div>

      <div className="flex min-w-0 items-center gap-3">
        <div
          className="relative grid h-10 w-10 place-items-center overflow-hidden rounded-md border border-border/75 text-[11px] font-semibold uppercase text-white"
          style={{
            backgroundImage: `linear-gradient(140deg, ${track.coverFrom}, ${track.coverTo})`,
          }}
        >
          {track.coverUrl ? (
            <img
              src={track.coverUrl}
              alt={`${track.title} Cover`}
              className="absolute inset-0 h-full w-full object-cover"
              loading="lazy"
              onError={(event) => {
                event.currentTarget.style.display = "none";
              }}
            />
          ) : null}
          <span>{track.artist.slice(0, 2)}</span>
        </div>
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-foreground">
            {track.title}
          </p>
          <p className="truncate text-sm text-muted-foreground">
            {track.artist}
          </p>
        </div>
      </div>

      <span className="text-sm text-foreground">{track.year}</span>
      <span className="text-[11px] uppercase tracking-[0.08em] text-muted-foreground">
        {track.genre}
      </span>

      <div className="flex items-center justify-end">
        <Button
          size="icon-xs"
          variant="outline"
          aria-label={`${track.title} entfernen`}
          onClick={() => removeTrack(track.id)}
        >
          <X className="size-3.5" />
        </Button>
      </div>
    </div>
  );

  const rightPanel = (
    <Card className="h-full rounded-none border-0 bg-card/55 py-0 shadow-none ring-0 md:rounded-none">
      <div className="flex h-full min-h-0 flex-col">
        <div className="border-b border-border/60 px-3 py-2 sm:px-4">
          <Tabs
            value={activeView}
            onValueChange={(value) => setActiveView(value as DeckViewMode)}
          >
            <div className="flex items-center justify-between gap-2">
              <TabsList variant="line" className="h-auto p-0">
                <TabsTrigger
                  value="playlist"
                  className="gap-1.5 rounded-none px-1.5 py-2 text-sm"
                >
                  <ListMusic className="size-4" />
                  Liste
                </TabsTrigger>
                <TabsTrigger
                  value="cards"
                  className="gap-1.5 rounded-none px-1.5 py-2 text-sm"
                >
                  <LayoutGrid className="size-4" />
                  Karten
                </TabsTrigger>
              </TabsList>
              <Badge
                variant="outline"
                className="h-6 px-2 text-[11px] uppercase tracking-[0.12em]"
              >
                {filteredTracks.length} / 50 Songs
              </Badge>
            </div>

            <TabsContent
              value="playlist"
              className="mt-2 flex min-h-0 flex-1 flex-col"
            >
              <div className="relative mb-2 px-0 sm:mb-3">
                <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  className="pl-9"
                  placeholder="Playlist durchsuchen: Titel, Artist, Jahr, Genre..."
                />
              </div>

              <div className="grid grid-cols-[52px_minmax(0,1fr)_70px_95px_44px] items-center px-1 pb-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                <span className="justify-self-center">#</span>
                <span>Titel</span>
                <span>Jahr</span>
                <span>Genre</span>
                <span />
              </div>

              <ScrollArea className="min-h-0 flex-1 pr-2">
                <div className="space-y-1 pb-3">
                  {filteredTracks.map(renderTrackRow)}
                </div>
                {filteredTracks.length === 0 ? (
                  <div className="px-3 py-8 text-center text-sm text-muted-foreground">
                    Keine Treffer in der Playlist.
                  </div>
                ) : null}
              </ScrollArea>
            </TabsContent>

            <TabsContent value="cards" className="mt-2 min-h-0 flex-1">
              <ScrollArea className="h-full pr-2">
                <div className="grid grid-cols-2 gap-3 pb-3 sm:grid-cols-3">
                  {Array.from({ length: 6 }).map((_, idx) => (
                    <Card
                      key={`card-placeholder-${idx}`}
                      size="sm"
                      className="gap-3 border border-border/70 bg-background/65 p-3"
                    >
                      <div className="h-24 rounded-md border border-dashed border-border/70 bg-muted/45" />
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

        <div className="mt-auto border-t border-border/60 p-3 sm:p-4">
          <div className="flex flex-wrap items-center justify-end gap-2.5">
            <Button variant="outline" onClick={() => navigate("/")}>
              <ArrowLeft className="size-4" />
              Zuruck zur Startseite
            </Button>
            <Button>
              Karten exportieren
              <ArrowUp className="size-4" />
            </Button>
          </div>
        </div>
      </div>
    </Card>
  );

  const leftPanel = (
    <Card className="h-full rounded-none border-0 bg-card/60 py-0 shadow-none ring-0">
      <aside className="flex h-full min-h-0 flex-col">
        <div className="flex items-center justify-between border-b border-border/60 px-3 py-3 sm:px-4">
          <PrompsterLogo
            className="gap-2.5"
            titleClassName="text-sm text-foreground"
            subtitle="Deck Assistant"
          />
          <Badge
            variant="secondary"
            className="h-6 gap-1 px-2 text-[11px] uppercase tracking-[0.08em]"
          >
            <Sparkles className="size-3" />
            Live
          </Badge>
        </div>

        <ScrollArea className="min-h-0 flex-1 p-3 sm:p-4">
          <div className="space-y-3 pr-1">
            {messages.map(renderMessageBubble)}
          </div>
        </ScrollArea>

        <div className="border-t border-border/60 p-3 sm:p-4">
          <ChatInputBox
            value={chatInput}
            onChange={setChatInput}
            onSubmit={sendChatMessage}
            placeholder="Antworte oder frag..."
            textareaClassName="max-h-40"
            rows={1}
          />
        </div>
      </aside>
    </Card>
  );

  return (
    <div className="h-dvh overflow-hidden bg-[radial-gradient(circle_at_14%_6%,_hsl(146_78%_22%)_0%,_transparent_40%),radial-gradient(circle_at_88%_0%,_hsl(201_82%_18%)_0%,_transparent_34%),linear-gradient(160deg,_hsl(222_48%_8%)_0%,_hsl(221_57%_5%)_100%)] text-foreground">
      <div className="mx-auto h-full w-full p-0">
        <div className="flex h-full min-h-0 flex-col md:hidden">
          <div className="h-[52dvh] min-h-[300px]">{leftPanel}</div>
          <div className="min-h-0 flex-1">{rightPanel}</div>
        </div>

        <div className="hidden h-full min-h-0 md:block">
          <ResizablePanelGroup
            orientation="horizontal"
            className="border border-border/65 bg-background/35 backdrop-blur-md"
          >
            <ResizablePanel defaultSize="32%" minSize="320px" maxSize="52%">
              {leftPanel}
            </ResizablePanel>
            <ResizableHandle
              withHandle
              className="w-2 cursor-col-resize bg-transparent hover:bg-border/70 data-[separator=active]:bg-primary/40"
            />
            <ResizablePanel defaultSize="68%">{rightPanel}</ResizablePanel>
          </ResizablePanelGroup>
        </div>
      </div>
    </div>
  );
};

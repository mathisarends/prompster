import { useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  ArrowUp,
  FileText,
  LayoutGrid,
  ListMusic,
  Mic,
  Paperclip,
  Play,
  Search,
  Sparkles,
  X,
} from "lucide-react";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
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
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
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

type ChatAttachment = {
  id: string;
  name: string;
  size: number;
  type?: string;
  previewUrl?: string;
};

const formatDuration = (seconds: number) => {
  const mins = Math.floor(seconds / 60)
    .toString()
    .padStart(2, "0");
  const secs = (seconds % 60).toString().padStart(2, "0");
  return `${mins}:${secs}`;
};

const formatSize = (bytes: number) => {
  if (bytes < 1024 * 1024) {
    return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

export const InteractiveDeckPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const state = (location.state as LocationState | null) ?? null;
  const [activeView, setActiveView] = useState<DeckViewMode>("playlist");
  const [tracks, setTracks] = useState(mockTracks);
  const [query, setQuery] = useState("");
  const [chatInput, setChatInput] = useState("");
  const [isMicActive, setIsMicActive] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(7);
  const [attachments, setAttachments] = useState<ChatAttachment[]>([]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const attachmentsRef = useRef<ChatAttachment[]>([]);

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

  useEffect(() => {
    if (!isMicActive) {
      return;
    }

    const timer = window.setInterval(() => {
      setRecordingSeconds((prev) => prev + 1);
    }, 1000);

    return () => window.clearInterval(timer);
  }, [isMicActive]);

  useEffect(() => {
    attachmentsRef.current = attachments;
  }, [attachments]);

  useEffect(() => {
    return () => {
      attachmentsRef.current.forEach((file) => {
        if (file.previewUrl) {
          URL.revokeObjectURL(file.previewUrl);
        }
      });
    };
  }, []);

  const addFiles = (fileList: FileList | null) => {
    if (!fileList || fileList.length === 0) {
      return;
    }

    const nextAttachments = Array.from(fileList).map((file) => ({
      id: `${file.name}-${file.size}-${file.lastModified}-${crypto.randomUUID()}`,
      name: file.name,
      size: file.size,
      type: file.type || undefined,
      previewUrl: file.type.startsWith("image/")
        ? URL.createObjectURL(file)
        : undefined,
    }));

    setAttachments((prev) => [...prev, ...nextAttachments]);
  };

  useEffect(() => {
    const onPaste = (event: ClipboardEvent) => {
      const fileList = event.clipboardData?.files;
      if (!fileList || fileList.length === 0) {
        return;
      }

      event.preventDefault();
      addFiles(fileList);
    };

    window.addEventListener("paste", onPaste);
    return () => window.removeEventListener("paste", onPaste);
  }, []);

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

  const removeAttachment = (id: string) => {
    setAttachments((prev) => {
      const target = prev.find((item) => item.id === id);
      if (target?.previewUrl) {
        URL.revokeObjectURL(target.previewUrl);
      }
      return prev.filter((item) => item.id !== id);
    });
  };

  const sendChatMessage = () => {
    const trimmed = chatInput.trim();
    if (!trimmed && attachments.length === 0) {
      return;
    }

    const attachmentSuffix =
      attachments.length > 0
        ? ` [${attachments.length} Datei(en): ${attachments.map((file) => file.name).join(", ")}]`
        : "";

    setMessages((prev) => [
      ...prev,
      {
        id: `user-${crypto.randomUUID()}`,
        role: "user",
        text: `${trimmed || "Datei gesendet"}${attachmentSuffix}`,
      },
      {
        id: `assistant-${crypto.randomUUID()}`,
        role: "assistant",
        text: "Verstanden. Ich aktualisiere jetzt die Vorschlage fur dein Deck.",
      },
    ]);

    setChatInput("");
    setAttachments((prev) => {
      prev.forEach((file) => {
        if (file.previewUrl) {
          URL.revokeObjectURL(file.previewUrl);
        }
      });
      return [];
    });
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const startVoiceRecording = () => {
    setRecordingSeconds(0);
    setIsMicActive(true);
  };

  const cancelVoiceRecording = () => {
    setIsMicActive(false);
    setRecordingSeconds(0);
  };

  const sendVoiceRecording = () => {
    setMessages((prev) => [
      ...prev,
      {
        id: `voice-${crypto.randomUUID()}`,
        role: "user",
        text: `Sprachnachricht gesendet (${formatDuration(recordingSeconds)})`,
      },
      {
        id: `assistant-voice-${crypto.randomUUID()}`,
        role: "assistant",
        text: "Audio ist angekommen. Ich ubernehme die Anpassung fur die Songliste.",
      },
    ]);
    cancelVoiceRecording();
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
          <div className="flex items-center gap-2.5">
            <Avatar className="size-8 rounded-md border border-border/70 bg-background/80">
              <AvatarFallback className="rounded-md text-xs font-semibold">
                P
              </AvatarFallback>
            </Avatar>
            <div>
              <p className="text-sm font-semibold text-foreground">Prompster</p>
              <p className="text-xs text-muted-foreground">Deck Assistant</p>
            </div>
          </div>
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
          {!isMicActive ? (
            <div className="overflow-hidden rounded-xl border border-border/70 bg-background/70">
              {attachments.length > 0 ? (
                <div className="overflow-x-auto px-2 pt-2">
                  <div className="flex w-max gap-2 pb-2 pr-1">
                    {attachments.map((file) => (
                      <div
                        key={file.id}
                        className="relative w-44 shrink-0 overflow-hidden rounded-xl border border-border/70 bg-background/65"
                      >
                        {file.previewUrl ? (
                          <img
                            src={file.previewUrl}
                            alt={`Vorschau von ${file.name}`}
                            className="h-24 w-full object-cover"
                          />
                        ) : (
                          <div className="grid h-24 place-items-center bg-muted/45 text-muted-foreground">
                            <FileText className="size-7" />
                          </div>
                        )}
                        <div className="space-y-0.5 p-2">
                          <p className="max-h-8 overflow-hidden break-words text-xs font-medium leading-tight text-foreground">
                            {file.name}
                          </p>
                          <p className="text-[11px] text-muted-foreground">
                            {formatSize(file.size)}
                          </p>
                        </div>
                        <Button
                          size="icon-xs"
                          variant="ghost"
                          className="absolute right-1 top-1 bg-background/85 hover:bg-background"
                          onClick={() => removeAttachment(file.id)}
                          aria-label={`${file.name} entfernen`}
                        >
                          <X className="size-3" />
                        </Button>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}

              <Textarea
                ref={textareaRef}
                rows={1}
                value={chatInput}
                onChange={(event) => setChatInput(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    sendChatMessage();
                  }
                }}
                placeholder="Antworte oder frag..."
                className="max-h-40 min-h-[42px] resize-none border-0 bg-transparent px-3 py-3 shadow-none focus-visible:ring-0"
              />

              <input
                ref={fileInputRef}
                type="file"
                multiple
                className="hidden"
                onChange={(event) => {
                  addFiles(event.target.files);
                  event.currentTarget.value = "";
                }}
              />

              <Separator />
              <div className="flex items-center justify-between px-2 py-2">
                <Button
                  size="icon-sm"
                  variant="ghost"
                  onClick={() => fileInputRef.current?.click()}
                  aria-label="Datei anhangen"
                >
                  <Paperclip className="size-4" />
                </Button>
                {chatInput.trim() ? (
                  <Button size="sm" onClick={sendChatMessage}>
                    Senden
                  </Button>
                ) : (
                  <Button
                    size="icon-sm"
                    variant="outline"
                    onClick={startVoiceRecording}
                    aria-label="Sprachnachricht aufnehmen"
                  >
                    <Mic className="size-4" />
                  </Button>
                )}
              </div>
            </div>
          ) : (
            <div className="rounded-xl border border-border/70 bg-background/85 p-2.5">
              <div className="flex items-center gap-2">
                <Button
                  size="icon-sm"
                  variant="outline"
                  aria-label="Mikrofon aktiv"
                >
                  <Mic className="size-4" />
                </Button>
                <div className="flex flex-1 items-end gap-1 px-1">
                  {[8, 14, 11, 17, 9, 16, 12, 18, 10, 15, 9, 14].map(
                    (height, idx) => (
                      <span
                        key={idx}
                        className="w-1 rounded-full bg-foreground/70"
                        style={{ height }}
                      />
                    ),
                  )}
                </div>
                <span className="min-w-11 text-right text-sm font-medium text-muted-foreground">
                  {formatDuration(recordingSeconds)}
                </span>
                <Button
                  size="icon-sm"
                  variant="ghost"
                  onClick={cancelVoiceRecording}
                >
                  <X className="size-4" />
                </Button>
                <Button size="icon-sm" onClick={sendVoiceRecording}>
                  <ArrowUp className="size-4" />
                </Button>
              </div>
            </div>
          )}
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

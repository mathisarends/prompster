import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, FileText, Plus, Sparkles, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { NavigationSidebar } from "@/components/navigation-sidebar";
import type { ChatHistoryEntry } from "@/lib/mockChats";
import { cn } from "@/lib/utils";
import { useLocalStorage } from "@/hooks/useLocalStorage";

type DraftAttachment = {
  id: string;
  name: string;
  size: number;
  type?: string;
  previewUrl?: string;
};

const formatSize = (bytes: number) => {
  if (bytes < 1024 * 1024) {
    return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

export const HomePage = () => {
  const [prompt, setPrompt] = useState("");
  const [sidebarOpen, setSidebarOpen] = useLocalStorage(
    "prompster.sidebar.open",
    true,
  );
  const [activeChatId, setActiveChatId] = useState<string | undefined>();
  const [attachments, setAttachments] = useState<DraftAttachment[]>([]);
  const [previewAttachment, setPreviewAttachment] =
    useState<DraftAttachment | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const attachmentsRef = useRef<DraftAttachment[]>([]);
  const navigate = useNavigate();

  const addFiles = (fileList: FileList | null) => {
    if (!fileList || fileList.length === 0) {
      return;
    }

    const nextFiles = Array.from(fileList).map((file) => ({
      id: `${file.name}-${file.size}-${file.lastModified}-${crypto.randomUUID()}`,
      name: file.name,
      size: file.size,
      type: file.type || undefined,
      previewUrl: file.type.startsWith("image/")
        ? URL.createObjectURL(file)
        : undefined,
    }));

    setAttachments((prev) => [...prev, ...nextFiles]);
  };

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

  const startChat = () => {
    navigate("/deck/mock", { state: { prompt, attachments } });
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

  const canStartChat = prompt.trim().length > 0 || attachments.length > 0;

  const handleSelectChat = (chat: ChatHistoryEntry) => {
    setActiveChatId(chat.id);
    navigate("/deck/mock", { state: { prompt: chat.title } });
  };

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_10%_5%,_hsl(141_78%_26%)_0%,_transparent_40%),radial-gradient(circle_at_88%_8%,_hsl(154_50%_16%)_0%,_transparent_22%),linear-gradient(165deg,_hsl(222_46%_8%)_0%,_hsl(222_52%_5%)_100%)] text-foreground">
      <NavigationSidebar
        open={sidebarOpen}
        onToggle={() => setSidebarOpen((prev) => !prev)}
        onSelectChat={handleSelectChat}
        activeChatId={activeChatId}
      />

      <main
        className={cn(
          "flex min-h-screen flex-col justify-center px-4 py-10 transition-[padding] duration-300 ease-out sm:px-8 sm:py-14",
          sidebarOpen ? "sm:pl-80" : "sm:pl-24",
        )}
      >
        <div className="mx-auto w-full max-w-4xl">
          <section className="space-y-8">
            <div className="space-y-4 text-center sm:space-y-5">
              <Badge
                variant="secondary"
                className="mx-auto w-fit gap-1 px-2.5 py-1"
              >
                <Sparkles className="size-3.5" />
                Neues Karten-Deck
              </Badge>
              <h1 className="mx-auto max-w-3xl text-4xl font-semibold tracking-tight sm:text-6xl">
                Welche Musik soll dein Deck haben?
              </h1>
              <p className="mx-auto max-w-2xl text-sm text-muted-foreground sm:text-lg">
                Beschreib dein Wunsch-Deck in einem Satz. Der Agent fragt
                gezielt nach und erstellt daraus Schritt fur Schritt dein Deck.
              </p>
            </div>

            <div className="space-y-2">
              <div className="rounded-2xl bg-card/55 p-4 backdrop-blur-md sm:p-5">
                {attachments.length > 0 ? (
                  <div className="mb-3 overflow-x-auto pb-1">
                    <div className="flex w-max gap-2 pr-1">
                      {attachments.map((file) => (
                        <div
                          key={file.id}
                          className="relative w-44 shrink-0 overflow-hidden rounded-xl border border-border/70 bg-background/60 cursor-pointer"
                          onClick={() => setPreviewAttachment(file)}
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
                            onClick={(e) => {
                              e.stopPropagation();
                              removeAttachment(file.id);
                            }}
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
                  className="min-h-17.5 resize-none border-none bg-transparent p-0 text-base md:text-base shadow-none focus-visible:ring-0"
                  placeholder='z.B. "Hip-Hop Klassiker der 90er fur 60 Karten" oder "Eurovision Hits 2000-2020"'
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
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

                <div className="flex items-center justify-between gap-3">
                  <Button
                    size="icon-sm"
                    variant="ghost"
                    onClick={() => fileInputRef.current?.click()}
                    aria-label="Datei anhangen"
                  >
                    <Plus className="size-4" />
                  </Button>
                  <Button onClick={startChat} disabled={!canStartChat}>
                    Chat starten
                    <ArrowRight className="size-4" />
                  </Button>
                </div>
              </div>
            </div>
          </section>
        </div>
      </main>

      <Dialog
        open={!!previewAttachment}
        onOpenChange={(open) => !open && setPreviewAttachment(null)}
      >
        <DialogContent className="max-w-3xl p-0 overflow-hidden rounded-2xl bg-card/90 backdrop-blur-md border-border/60">
          {previewAttachment?.previewUrl ? (
            <img
              src={previewAttachment.previewUrl}
              alt={previewAttachment.name}
              className="w-full max-h-[80vh] object-contain"
            />
          ) : (
            <div className="grid h-64 place-items-center text-muted-foreground">
              <FileText className="size-16" />
            </div>
          )}
          <div className="px-5 py-3 border-t border-border/50">
            <p className="text-sm font-medium text-foreground">
              {previewAttachment?.name}
            </p>
            <p className="text-xs text-muted-foreground">
              {previewAttachment ? formatSize(previewAttachment.size) : ""}
            </p>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

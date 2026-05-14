import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { FileText, Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { ChatInputBox, type ChatAttachment } from "@/components/chat-input-box";
import { NavigationSidebar } from "@/components/navigation-sidebar";
import type { ChatHistoryEntry } from "@/lib/mockChats";
import { cn } from "@/lib/utils";
import { useLocalStorage } from "@/hooks/useLocalStorage";

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
  const [previewAttachment, setPreviewAttachment] =
    useState<ChatAttachment | null>(null);
  const navigate = useNavigate();

  const handleSelectChat = (chat: ChatHistoryEntry) => {
    setActiveChatId(chat.id);
    navigate("/deck/mock", { state: { prompt: chat.title } });
  };

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_8%_0%,_hsl(141_52%_24%_/_0.12)_0%,_transparent_34%),radial-gradient(circle_at_94%_0%,_hsl(214_62%_24%_/_0.1)_0%,_transparent_24%),linear-gradient(165deg,_hsl(222_46%_8%)_0%,_hsl(222_52%_5%)_100%)] text-foreground">
      <NavigationSidebar
        open={sidebarOpen}
        onToggle={() => setSidebarOpen((prev) => !prev)}
        onSelectChat={handleSelectChat}
        activeChatId={activeChatId}
      />

      <main
        className={cn(
          "flex min-h-screen flex-col justify-start px-4 pb-10 pt-8 transition-[padding] duration-300 ease-out sm:px-8 sm:pb-14 sm:pt-10 lg:pt-12",
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
              <ChatInputBox
                value={prompt}
                onChange={setPrompt}
                onSubmit={(text, attachments) =>
                  navigate("/deck/mock", {
                    state: { prompt: text, attachments },
                  })
                }
                placeholder='z.B. "Hip-Hop Klassiker der 90er fur 60 Karten" oder "Eurovision Hits 2000-2020"'
                sendButtonAriaLabel="Chat starten"
                onAttachmentClick={setPreviewAttachment}
              />
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

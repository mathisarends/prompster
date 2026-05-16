import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { FileText, Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { ChatInputBox, type ChatAttachment } from "@/components/chat-input-box";

const formatSize = (bytes: number) => {
  if (bytes < 1024 * 1024) {
    return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

export const HomePage = () => {
  const [prompt, setPrompt] = useState("");
  const [previewAttachment, setPreviewAttachment] =
    useState<ChatAttachment | null>(null);
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    if (location.state && "newChatAt" in location.state) {
      setPrompt("");
    }
  }, [location.state]);

  return (
    <div className="home-page-background min-h-dvh text-foreground">
      <main className="relative z-10 flex min-h-dvh flex-col justify-center px-4 py-10 sm:px-8 sm:py-14">
        <div className="mx-auto w-full max-w-4xl -translate-y-6 sm:-translate-y-8">
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

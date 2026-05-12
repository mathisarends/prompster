import { useEffect, useRef, useState } from "react";
import { ArrowUp, Mic, Paperclip, Plus } from "lucide-react";
import { Button } from "../Button";

type ChatRole = "user" | "assistant";

type ChatMessage = {
  id: string;
  role: ChatRole;
  text: string;
};

type ChatAttachment = {
  id: string;
  name: string;
  size: number;
};

type ChatSidebarProps = {
  initialPrompt?: string;
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

export const ChatSidebar = ({ initialPrompt }: ChatSidebarProps) => {
  const [chatInput, setChatInput] = useState("");
  const [isMicActive, setIsMicActive] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [recordingSeconds, setRecordingSeconds] = useState(7);
  const [attachments, setAttachments] = useState<ChatAttachment[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    const seed = initialPrompt || "Lass uns ein 80er/90er Pop Deck bauen.";
    return [
      {
        id: "assistant-1",
        role: "assistant",
        text: "Top, ich erstelle mit dir jetzt Schritt fur Schritt ein Deck.",
      },
      { id: "user-1", role: "user", text: seed },
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
    const onPaste = (event: ClipboardEvent) => {
      const fileList = event.clipboardData?.files;
      if (!fileList || fileList.length === 0) {
        return;
      }

      event.preventDefault();
      const nextItems = Array.from(fileList).map((file) => ({
        id: `${file.name}-${file.size}-${crypto.randomUUID()}`,
        name: file.name,
        size: file.size,
      }));
      setAttachments((prev) => [...prev, ...nextItems]);
    };

    window.addEventListener("paste", onPaste);
    return () => window.removeEventListener("paste", onPaste);
  }, []);

  const removeAttachment = (id: string) => {
    setAttachments((prev) => prev.filter((item) => item.id !== id));
  };

  const sendChatMessage = () => {
    const trimmed = chatInput.trim();
    if (!trimmed && attachments.length === 0) {
      return;
    }

    const attachmentLabel =
      attachments.length > 0
        ? ` [${attachments.length} Datei(en): ${attachments.map((file) => file.name).join(", ")}]`
        : "";

    setMessages((prev) => [
      ...prev,
      {
        id: `user-${crypto.randomUUID()}`,
        role: "user",
        text: `${trimmed || "Datei gesendet"}${attachmentLabel}`,
      },
      {
        id: `assistant-${crypto.randomUUID()}`,
        role: "assistant",
        text: "Verstanden. Ich aktualisiere jetzt die Vorschlage fur dein Deck.",
      },
    ]);

    setChatInput("");
    setAttachments([]);
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setChatInput(e.target.value);
    e.target.style.height = "auto";
    e.target.style.height = `${e.target.scrollHeight}px`;
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendChatMessage();
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

  return (
    <aside className="flex h-full flex-col border-r border-[var(--beatline-border)] bg-[var(--beatline-surface)]/65">
      <div className="flex items-center justify-between border-b border-[var(--beatline-border)] px-4 py-3">
        <div className="flex items-center gap-2">
          <div className="grid h-8 w-8 place-items-center rounded-md border border-[var(--beatline-border)] bg-[var(--beatline-bg)] text-xs font-semibold">
            P
          </div>
          <span className="text-lg font-semibold">Prompster</span>
        </div>
      </div>

      <div className="min-h-0 flex-1 space-y-3 overflow-auto p-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`max-w-[92%] rounded-lg border px-3 py-2 text-sm leading-relaxed ${
              message.role === "user"
                ? "ml-auto border-[var(--beatline-gold-dark)] bg-[var(--beatline-highlight)] text-[var(--beatline-text)]"
                : "border-[var(--beatline-border)] bg-[var(--beatline-bg)]/80 text-[var(--beatline-muted)]"
            }`}
          >
            {message.text}
          </div>
        ))}
      </div>

      <div className="relative mt-auto p-4">
        <div className="pointer-events-none absolute inset-x-0 -top-8 h-8 bg-gradient-to-t from-[var(--beatline-surface)]/65 to-transparent" />

        {attachments.length > 0 && (
          <div className="mb-3 flex flex-wrap gap-2">
            {attachments.map((file) => (
              <div
                key={file.id}
                className="flex items-center gap-2 rounded-full border border-[var(--beatline-border)] bg-[var(--beatline-bg)]/80 px-3 py-1 text-xs text-[var(--beatline-muted)]"
              >
                <span className="max-w-28 truncate">{file.name}</span>
                <span>{formatSize(file.size)}</span>
                <Button
                  variant="ghost"
                  className="rounded border border-[var(--beatline-border)] px-1 leading-none hover:border-[var(--beatline-gold-dark)]"
                  onClick={() => removeAttachment(file.id)}
                >
                  x
                </Button>
              </div>
            ))}
          </div>
        )}

        {!isMicActive ? (
          <div className="overflow-hidden rounded-xl border border-[var(--beatline-border)] bg-[var(--beatline-bg)]/80 shadow-lg">
            <textarea
              ref={textareaRef}
              className="max-h-48 min-h-[36px] w-full resize-none bg-transparent px-3 py-3 text-sm text-[var(--beatline-text)] outline-none placeholder:text-[var(--beatline-subtle)]"
              placeholder="Antworte oder frag..."
              rows={1}
              value={chatInput}
              onChange={handleTextareaChange}
              onKeyDown={handleKeyDown}
            />
            <div className="flex items-center justify-between px-2 py-2">
              <div className="flex items-center gap-2">
                <button
                  className="grid place-items-center rounded-md border border-[var(--beatline-border)] p-1.5 text-[var(--beatline-muted)] hover:border-[var(--beatline-gold-dark)]"
                  type="button"
                >
                  <Paperclip size={16} />
                </button>
              </div>
              {chatInput.trim() ? (
                <Button className="py-1.5" onClick={sendChatMessage}>
                  Senden
                </Button>
              ) : (
                <button
                  className="grid place-items-center rounded-md border border-[var(--beatline-border)] p-1.5 text-[var(--beatline-muted)] hover:border-[var(--beatline-gold-dark)]"
                  onClick={startVoiceRecording}
                  type="button"
                >
                  <Mic size={16} />
                </button>
              )}
            </div>
          </div>
        ) : (
          <div className="rounded-xl border-2 border-[var(--beatline-border)] bg-[var(--beatline-bg)]/90 px-3 py-2">
            <div className="flex items-center gap-3">
              <button
                className="relative grid h-9 w-9 place-items-center rounded-md border border-[var(--beatline-border)] bg-[var(--beatline-bg)] text-[var(--beatline-text)]"
                type="button"
              >
                <Mic size={16} />
                <span className="absolute right-1 top-1 h-2 w-2 rounded-full bg-[#e86f5d]" />
              </button>
              <div className="flex flex-1 items-center gap-1">
                {[8, 14, 11, 17, 9, 16, 12, 18, 10, 15, 9, 14].map(
                  (height, idx) => (
                    <span
                      key={idx}
                      className="w-1 rounded-full bg-[var(--beatline-text)]/75"
                      style={{ height }}
                    />
                  ),
                )}
              </div>
              <span className="text-sm font-semibold text-[var(--beatline-muted)]">
                {formatDuration(recordingSeconds)}
              </span>
              <Button
                variant="ghost"
                className="rounded-md border border-[var(--beatline-border)] px-3 py-1.5 text-sm text-[var(--beatline-muted)] hover:border-[var(--beatline-gold-dark)]"
                onClick={cancelVoiceRecording}
              >
                x
              </Button>
              <button
                className="grid place-items-center rounded-md border border-[var(--beatline-gold-dark)] bg-[var(--beatline-gold)] p-1.5 text-[#2D2D44] transition-colors hover:bg-[var(--beatline-gold-dark)]"
                onClick={sendVoiceRecording}
                type="button"
              >
                <ArrowUp size={16} />
              </button>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
};

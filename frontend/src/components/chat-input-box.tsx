import { useEffect, useId, useRef, useState } from "react";
import { ArrowUp, FileText, Plus, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

export type ChatAttachment = {
  id: string;
  name: string;
  size: number;
  type?: string;
  previewUrl?: string;
};

type ChatInputBoxProps = {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (text: string, attachments: ChatAttachment[]) => void;
  placeholder?: string;
  className?: string;
  textareaClassName?: string;
  rows?: number;
  showSeparator?: boolean;
  onAttachmentClick?: (attachment: ChatAttachment) => void;
  showAttachmentButton?: boolean;
  onOpenFileDialog?: () => void;
  sendButtonAriaLabel?: string;
};

const formatSize = (bytes: number) => {
  if (bytes < 1024 * 1024) {
    return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

export const ChatInputBox = ({
  value,
  onChange,
  onSubmit,
  placeholder,
  className,
  textareaClassName,
  rows,
  showSeparator = false,
  onAttachmentClick,
  showAttachmentButton = true,
  onOpenFileDialog,
  sendButtonAriaLabel = "Nachricht senden",
}: ChatInputBoxProps) => {
  const [attachments, setAttachments] = useState<ChatAttachment[]>([]);
  const fileInputId = useId();
  const attachmentsRef = useRef<ChatAttachment[]>([]);

  useEffect(() => {
    attachmentsRef.current = attachments;
  }, [attachments]);

  useEffect(() => {
    return () => {
      attachmentsRef.current.forEach((file) => {
        if (file.previewUrl) URL.revokeObjectURL(file.previewUrl);
      });
    };
  }, []);

  const addFiles = (fileList: FileList | null) => {
    if (!fileList || fileList.length === 0) return;

    const next = Array.from(fileList).map((file) => ({
      id: `${file.name}-${file.size}-${file.lastModified}-${crypto.randomUUID()}`,
      name: file.name,
      size: file.size,
      type: file.type || undefined,
      previewUrl: file.type.startsWith("image/")
        ? URL.createObjectURL(file)
        : undefined,
    }));

    setAttachments((prev) => [...prev, ...next]);
  };

  useEffect(() => {
    const onPaste = (event: ClipboardEvent) => {
      const files = event.clipboardData?.files;
      if (!files || files.length === 0) return;
      event.preventDefault();
      addFiles(files);
    };

    window.addEventListener("paste", onPaste);
    return () => window.removeEventListener("paste", onPaste);
  }, []);

  const removeAttachment = (id: string) => {
    setAttachments((prev) => {
      const target = prev.find((item) => item.id === id);
      if (target?.previewUrl) URL.revokeObjectURL(target.previewUrl);
      return prev.filter((item) => item.id !== id);
    });
  };

  const submit = () => {
    const trimmed = value.trim();
    if (!trimmed && attachments.length === 0) return;

    onSubmit(trimmed, attachments);
    onChange("");

    setAttachments((prev) => {
      prev.forEach((file) => {
        if (file.previewUrl) URL.revokeObjectURL(file.previewUrl);
      });
      return [];
    });
  };

  const canSubmit = value.trim().length > 0 || attachments.length > 0;

  const openFileDialog = () => {
    const input = document.getElementById(fileInputId);
    if (input instanceof HTMLInputElement) {
      input.click();
    }
    onOpenFileDialog?.();
  };

  return (
    <div
      className={cn(
        "overflow-hidden rounded-2xl bg-card/55 p-4 backdrop-blur-md sm:p-5",
        className,
      )}
    >
      {attachments.length > 0 && (
        <div className="overflow-x-auto px-2 pt-2">
          <div className="flex w-max gap-2 pb-2 pr-1">
            {attachments.map((file) => (
              <div
                key={file.id}
                className={cn(
                  "relative w-44 shrink-0 overflow-hidden rounded-xl border border-border/70 bg-background/65",
                  onAttachmentClick && "cursor-pointer",
                )}
                onClick={() => onAttachmentClick?.(file)}
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
      )}

      <Textarea
        rows={rows}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            submit();
          }
        }}
        placeholder={placeholder}
        className={cn(
          "min-h-17.5 resize-none border-none bg-transparent p-0 text-base shadow-none focus-visible:ring-0 md:text-base",
          textareaClassName,
        )}
      />

      <input
        id={fileInputId}
        type="file"
        multiple
        className="hidden"
        onChange={(event) => {
          addFiles(event.target.files);
          event.currentTarget.value = "";
        }}
      />

      {showSeparator && <Separator />}

      <div className="flex items-center justify-between gap-3">
        {showAttachmentButton ? (
          <Button
            size="icon"
            variant="ghost"
            onClick={openFileDialog}
            aria-label="Datei anhangen"
          >
            <Plus className="size-4" />
          </Button>
        ) : (
          <div />
        )}

        <Button
          size="icon"
          onClick={submit}
          disabled={!canSubmit}
          aria-label={sendButtonAriaLabel}
        >
          <ArrowUp className="size-4 text-white" />
        </Button>
      </div>
    </div>
  );
};

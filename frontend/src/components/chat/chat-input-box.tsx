import { type MouseEvent, useEffect, useRef, useState } from "react";

import { AttachmentList } from "@/components/chat/attachments/attachment-list";
import { AttachmentPopover } from "@/components/chat/attachments/attachment-popover";
import type { ChatAttachment } from "@/components/chat/attachments/attachment-types";
import { SendButton } from "@/components/chat/send-button";
import { TranscriptionButton } from "@/components/chat/transcription-button";
import { Textarea } from "@/components/ui/textarea";
import { useRealtimeTranscription } from "@/hooks/useRealtimeTranscription";
import { cn } from "@/lib/utils";

type ChatInputBoxProps = {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (text: string, attachments: ChatAttachment[]) => void | Promise<void>;
  placeholder?: string;
  className?: string;
  textareaClassName?: string;
  rows?: number;
  sendButtonAriaLabel?: string;
  disabled?: boolean;
  isSubmitting?: boolean;
  clearOnSubmit?: boolean;
  focusOnTyping?: boolean;
  showDisclaimer?: boolean;
  disclaimerText?: string;
  attachments?: ChatAttachment[];
  onAttachmentsChange?: (attachments: ChatAttachment[]) => void;
};

const isEditableElement = (element: EventTarget | null) => {
  if (!(element instanceof HTMLElement)) return false;

  return (
    element.isContentEditable ||
    element.closest("input, textarea, select, [contenteditable='true']") !==
      null
  );
};

const isVisible = (element: HTMLElement) => {
  const rect = element.getBoundingClientRect();
  const style = window.getComputedStyle(element);

  return (
    rect.width > 0 &&
    rect.height > 0 &&
    style.display !== "none" &&
    style.visibility !== "hidden"
  );
};

const isTextEntryKey = (event: KeyboardEvent) => {
  return (
    event.key.length === 1 &&
    !event.ctrlKey &&
    !event.metaKey &&
    !event.altKey &&
    !event.isComposing
  );
};

const isInteractiveElement = (element: EventTarget | null) => {
  if (!(element instanceof HTMLElement)) return false;

  return (
    element.closest(
      "button, a, input, textarea, select, [role='button'], [contenteditable='true']",
    ) !== null
  );
};

const attachmentKey = (attachment: ChatAttachment) =>
  `${attachment.kind}:${attachment.id}`;

export const ChatInputBox = ({
  value,
  onChange,
  onSubmit,
  placeholder,
  className,
  textareaClassName,
  rows,
  sendButtonAriaLabel = "Nachricht senden",
  disabled = false,
  isSubmitting = false,
  clearOnSubmit = true,
  focusOnTyping = true,
  showDisclaimer = false,
  disclaimerText = "Prompster ist eine KI und kann Fehler machen. Bitte überprüfe die Antworten.",
  attachments: controlledAttachments,
  onAttachmentsChange,
}: ChatInputBoxProps) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const inputContentRef = useRef<HTMLDivElement>(null);
  const textMirrorRef = useRef<HTMLDivElement>(null);
  const [isSingleLine, setIsSingleLine] = useState(true);
  const [internalAttachments, setInternalAttachments] = useState<
    ChatAttachment[]
  >([]);
  const attachments = controlledAttachments ?? internalAttachments;
  const setAttachments = (next: ChatAttachment[]) => {
    if (controlledAttachments === undefined) {
      setInternalAttachments(next);
    }
    onAttachmentsChange?.(next);
  };

  const {
    error: transcriptionError,
    isRecording,
    isStarting: isStartingRecording,
    start: startTranscription,
    stop: stopTranscription,
  } = useRealtimeTranscription({
    value,
    onTranscriptChange: onChange,
    disabled: disabled || isSubmitting,
  });
  const hasText = value.trim().length > 0;
  const hasAttachments = attachments.length > 0;
  const canSend = hasText || hasAttachments;
  const showSendButton = canSend && !isRecording && !isStartingRecording;
  const showTranscriptionButton =
    !canSend || isRecording || isStartingRecording;

  useEffect(() => {
    if (!focusOnTyping) return;

    const focusChatInputOnTyping = (event: KeyboardEvent) => {
      const textarea = textareaRef.current;
      const dialogOpen = document.querySelector(
        "[data-slot='dialog-content'][data-open]",
      );

      if (
        !textarea ||
        event.defaultPrevented ||
        document.activeElement === textarea ||
        dialogOpen ||
        !isTextEntryKey(event) ||
        !isVisible(textarea) ||
        isEditableElement(event.target)
      ) {
        return;
      }

      textarea.focus();
    };

    window.addEventListener("keydown", focusChatInputOnTyping);
    return () => {
      window.removeEventListener("keydown", focusChatInputOnTyping);
    };
  }, [focusOnTyping]);

  const submit = () => {
    const trimmed = value.trim();
    if (!canSend || disabled || isSubmitting) return;

    if (isRecording || isStartingRecording) {
      void stopTranscription();
    }
    onSubmit(trimmed, attachments);
    if (clearOnSubmit) {
      onChange("");
      setAttachments([]);
    }
  };

  const toggleTranscription = () => {
    if (isRecording || isStartingRecording) {
      void stopTranscription();
      return;
    }

    void startTranscription();
  };

  const addAttachment = (attachment: ChatAttachment) => {
    const key = attachmentKey(attachment);
    if (attachments.some((existing) => attachmentKey(existing) === key)) return;
    setAttachments([...attachments, attachment]);
  };

  const removeAttachment = (attachment: ChatAttachment) => {
    const key = attachmentKey(attachment);
    setAttachments(attachments.filter((a) => attachmentKey(a) !== key));
  };

  const focusTextareaFromContainer = (event: MouseEvent<HTMLDivElement>) => {
    if (isInteractiveElement(event.target)) return;

    textareaRef.current?.focus();
  };

  useEffect(() => {
    const textarea = textareaRef.current;
    const inputContent = inputContentRef.current;
    const textMirror = textMirrorRef.current;
    if (!textarea || !inputContent || !textMirror) return;

    const measureSingleLine = () => {
      const styles = window.getComputedStyle(textarea);
      const inlineTextareaWidth = Math.max(inputContent.clientWidth - 88, 0);
      textMirror.style.width = `${inlineTextareaWidth}px`;

      const lineHeight =
        Number.parseFloat(styles.lineHeight) ||
        Number.parseFloat(styles.fontSize) * 1.2;
      const singleLineHeight = Math.ceil(lineHeight);
      const nextIsSingleLine = textMirror.scrollHeight <= singleLineHeight + 1;

      setIsSingleLine(nextIsSingleLine);
    };

    measureSingleLine();

    const resizeObserver = new ResizeObserver(measureSingleLine);
    resizeObserver.observe(inputContent);

    return () => {
      resizeObserver.disconnect();
    };
  }, [hasText, isRecording, placeholder, value]);

  return (
    <div className="flex flex-col">
      <div
        onClick={focusTextareaFromContainer}
        className={cn(
          "overflow-hidden rounded-2xl bg-card/55 px-5 py-3.5 backdrop-blur-md sm:p4 cursor-text",
          className,
        )}
      >
        {hasAttachments && (
          <AttachmentList
            attachments={attachments}
            onRemove={removeAttachment}
          />
        )}

        <div
          ref={inputContentRef}
          className={cn(
            isSingleLine
              ? "relative flex items-center gap-2"
              : "relative flex flex-col gap-3",
          )}
        >
          <div
            ref={textMirrorRef}
            aria-hidden="true"
            className="pointer-events-none absolute -z-10 whitespace-pre-wrap break-words p-0 text-base opacity-0 md:text-base"
          >
            {(value || placeholder || " ").endsWith("\n")
              ? `${value || placeholder || " "}\n `
              : value || placeholder || " "}
          </div>

          {isSingleLine && (
            <AttachmentPopover
              attachments={attachments}
              onAdd={addAttachment}
              disabled={disabled || isSubmitting}
            />
          )}

          <Textarea
            ref={textareaRef}
            rows={rows ?? 1}
            value={value}
            disabled={disabled || isSubmitting}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit();
              }
            }}
            placeholder={placeholder}
            className={cn(
              "max-h-72 min-h-9 flex-1 resize-none border-none bg-transparent p-0 pt-0.5 text-base shadow-none focus-visible:ring-0 md:text-base",
              !isSingleLine && "min-h-15",
              textareaClassName,
            )}
          />

          <div
            className={cn(
              "flex items-center gap-1.5",
              isSingleLine ? "shrink-0" : "justify-between",
            )}
          >
            {!isSingleLine && (
              <AttachmentPopover
                attachments={attachments}
                onAdd={addAttachment}
                disabled={disabled || isSubmitting}
              />
            )}
            <div className="flex items-center gap-1.5">
              {showTranscriptionButton && (
                <TranscriptionButton
                  isRecording={isRecording}
                  isStarting={isStartingRecording}
                  disabled={disabled || isSubmitting}
                  onClick={toggleTranscription}
                />
              )}
              {showSendButton && (
                <SendButton
                  onClick={submit}
                  disabled={disabled}
                  isLoading={isSubmitting}
                  ariaLabel={sendButtonAriaLabel}
                />
              )}
            </div>
          </div>
        </div>
      </div>
      {transcriptionError && (
        <p className="mt-2 text-center text-xs text-destructive">
          {transcriptionError}
        </p>
      )}
      {showDisclaimer && (
        <p className="mt-2 text-center text-xs text-muted-foreground">
          {disclaimerText}
        </p>
      )}
    </div>
  );
};

import { type MouseEvent, useEffect, useRef, useState } from "react";

import { AttachmentList } from "@/components/chat/attachments/attachment-list";
import { AttachmentPopover } from "@/components/chat/attachments/attachment-popover";
import type { ChatAttachment } from "@/components/chat/attachments/attachment-types";
import { SendButton } from "@/components/chat/send-button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

type AttachmentMention = {
  start: number;
  end: number;
  query: string;
};

type ChatInputBoxProps = {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (
    text: string,
    attachments: ChatAttachment[],
  ) => void | Promise<void>;
  placeholder?: string;
  className?: string;
  textareaClassName?: string;
  rows?: number;
  sendButtonAriaLabel?: string;
  disabled?: boolean;
  isSubmitting?: boolean;
  clearOnSubmit?: boolean;
  showDisclaimer?: boolean;
  disclaimerText?: string;
  attachments?: ChatAttachment[];
  onAttachmentsChange?: (attachments: ChatAttachment[]) => void;
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

const findAttachmentMention = (
  text: string,
  cursorPosition: number,
): AttachmentMention | null => {
  const beforeCursor = text.slice(0, cursorPosition);
  const start = beforeCursor.lastIndexOf("@");
  if (start < 0) return null;

  const previousCharacter = start > 0 ? text[start - 1] : "";
  if (previousCharacter && !/\s/.test(previousCharacter)) return null;

  const query = beforeCursor.slice(start + 1);
  if (query.includes("\n")) return null;

  return { start, end: cursorPosition, query };
};

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
  showDisclaimer = false,
  disclaimerText = "Prompster ist eine KI und kann Fehler machen. Bitte überprüfe die Antworten.",
  attachments: controlledAttachments,
  onAttachmentsChange,
}: ChatInputBoxProps) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const inputContentRef = useRef<HTMLDivElement>(null);
  const textMirrorRef = useRef<HTMLDivElement>(null);
  const textareaSelectionRef = useRef({ start: 0, end: 0 });
  const [isSingleLine, setIsSingleLine] = useState(true);
  const [attachmentPopoverOpen, setAttachmentPopoverOpen] = useState(false);
  const [attachmentMention, setAttachmentMention] =
    useState<AttachmentMention | null>(null);
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
  const hasText = value.trim().length > 0;
  const hasAttachments = attachments.length > 0;
  const canSend = hasText || hasAttachments;
  const isAttachmentMentionActive =
    attachmentPopoverOpen && !!attachmentMention;

  const updateAttachmentMention = (
    nextValue: string,
    cursorPosition: number | null,
  ) => {
    if (cursorPosition === null) return;

    const nextMention = findAttachmentMention(nextValue, cursorPosition);
    setAttachmentMention(nextMention);
    setAttachmentPopoverOpen(nextMention !== null);
  };

  const rememberTextareaSelection = (textarea: HTMLTextAreaElement) => {
    textareaSelectionRef.current = {
      start: textarea.selectionStart,
      end: textarea.selectionEnd,
    };
  };

  const focusTextareaAt = (position: number) => {
    requestAnimationFrame(() => {
      textareaRef.current?.focus();
      textareaRef.current?.setSelectionRange(position, position);
    });
  };

  const submit = () => {
    const trimmed = value.trim();
    if (!canSend || disabled || isSubmitting) return;

    onSubmit(trimmed, attachments);
    if (clearOnSubmit) {
      onChange("");
      setAttachments([]);
    }
  };

  const addAttachment = (attachment: ChatAttachment) => {
    const key = attachmentKey(attachment);
    if (attachments.some((existing) => attachmentKey(existing) === key)) return;
    setAttachments([...attachments, attachment]);
  };

  const removeAttachmentMention = () => {
    if (!attachmentMention) return;

    const nextValue = `${value.slice(0, attachmentMention.start)}${value.slice(
      attachmentMention.end,
    )}`;
    const nextCursorPosition = attachmentMention.start;

    onChange(nextValue);
    setAttachmentMention(null);
    setAttachmentPopoverOpen(false);

    focusTextareaAt(nextCursorPosition);
  };

  const closeAttachmentMention = () => {
    const cursorPosition = attachmentMention?.end ?? value.length;

    setAttachmentPopoverOpen(false);
    setAttachmentMention(null);
    focusTextareaAt(cursorPosition);
  };

  const startAttachmentMentionFromTrigger = () => {
    if (isAttachmentMentionActive) {
      closeAttachmentMention();
      return;
    }

    const textarea = textareaRef.current;
    const storedSelection = textareaSelectionRef.current;
    const selectionStart = Math.min(
      textarea?.selectionStart ?? storedSelection.start,
      value.length,
    );
    const selectionEnd = Math.min(
      textarea?.selectionEnd ?? storedSelection.end,
      value.length,
    );
    const characterBeforeCursor =
      selectionStart > 0 ? value[selectionStart - 1] : "";
    const leadingSpace =
      characterBeforeCursor && !/\s/.test(characterBeforeCursor) ? " " : "";
    const mentionStart = selectionStart + leadingSpace.length;
    const mentionEnd = mentionStart + 1;
    const nextValue = `${value.slice(
      0,
      selectionStart,
    )}${leadingSpace}@${value.slice(selectionEnd)}`;

    onChange(nextValue);
    setAttachmentMention({ start: mentionStart, end: mentionEnd, query: "" });
    setAttachmentPopoverOpen(true);
    textareaSelectionRef.current = { start: mentionEnd, end: mentionEnd };
  };

  const syncAttachmentMentionQuery = (nextQuery: string) => {
    if (!attachmentMention) return;

    const nextEnd = attachmentMention.start + 1 + nextQuery.length;
    const nextValue = `${value.slice(0, attachmentMention.start + 1)}${nextQuery}${value.slice(
      attachmentMention.end,
    )}`;

    onChange(nextValue);
    setAttachmentMention({
      ...attachmentMention,
      end: nextEnd,
      query: nextQuery,
    });
    setAttachmentPopoverOpen(true);
  };

  const handleAttachmentPopoverOpenChange = (nextOpen: boolean) => {
    if (nextOpen) {
      if (attachmentMention) {
        setAttachmentPopoverOpen(true);
      }
      return;
    }

    closeAttachmentMention();
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
  }, [hasText, placeholder, value]);

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
              open={attachmentPopoverOpen}
              onOpenChange={handleAttachmentPopoverOpenChange}
              onTriggerClick={startAttachmentMentionFromTrigger}
              query={
                isAttachmentMentionActive ? attachmentMention.query : undefined
              }
              onQueryChange={
                isAttachmentMentionActive
                  ? syncAttachmentMentionQuery
                  : undefined
              }
              onPick={
                isAttachmentMentionActive ? removeAttachmentMention : undefined
              }
            />
          )}

          <Textarea
            ref={textareaRef}
            rows={rows ?? 1}
            value={value}
            disabled={disabled || isSubmitting}
            onChange={(e) => {
              rememberTextareaSelection(e.target);
              onChange(e.target.value);
              updateAttachmentMention(e.target.value, e.target.selectionStart);
            }}
            onSelect={(e) => {
              rememberTextareaSelection(e.currentTarget);
              updateAttachmentMention(
                e.currentTarget.value,
                e.currentTarget.selectionStart,
              );
            }}
            onKeyDown={(e) => {
              if (isAttachmentMentionActive) {
                if (
                  e.key === "ArrowDown" ||
                  e.key === "ArrowUp" ||
                  e.key === "Enter"
                ) {
                  e.preventDefault();
                  return;
                }

                if (e.key === "Escape") {
                  e.preventDefault();
                  setAttachmentPopoverOpen(false);
                  setAttachmentMention(null);
                  focusTextareaAt(e.currentTarget.selectionStart);
                  return;
                }
              }

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
                open={attachmentPopoverOpen}
                onOpenChange={handleAttachmentPopoverOpenChange}
                onTriggerClick={startAttachmentMentionFromTrigger}
                query={
                  isAttachmentMentionActive
                    ? attachmentMention.query
                    : undefined
                }
                onQueryChange={
                  isAttachmentMentionActive
                    ? syncAttachmentMentionQuery
                    : undefined
                }
                onPick={
                  isAttachmentMentionActive
                    ? removeAttachmentMention
                    : undefined
                }
              />
            )}
            <div className="flex items-center gap-1.5">
              <SendButton
                onClick={submit}
                disabled={disabled || !canSend}
                isLoading={isSubmitting}
                ariaLabel={sendButtonAriaLabel}
              />
            </div>
          </div>
        </div>
      </div>
      {showDisclaimer && (
        <p className="mt-2 text-center text-xs text-muted-foreground">
          {disclaimerText}
        </p>
      )}
    </div>
  );
};

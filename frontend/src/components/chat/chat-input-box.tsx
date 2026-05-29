import {
  memo,
  type MouseEvent,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import { AttachmentList } from "@/components/chat/attachments/attachment-list";
import { AttachmentPopover } from "@/components/chat/attachments/attachment-popover";
import type { ChatAttachment } from "@/components/chat/attachments/attachment-types";
import { SendButton } from "@/components/chat/send-button";
import { useChatInputAttachments } from "@/components/chat/use-chat-input-attachments";
import { Textarea } from "@/components/ui/textarea";
import { useBufferedControlledValue } from "@/hooks/useBufferedControlledValue";
import { cn } from "@/lib/utils";

const DRAFT_SYNC_DELAY_MS = 180;

type ChatInputBoxProps = {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (
    text: string,
    attachments: ChatAttachment[],
  ) => void | Promise<void>;
  onStop?: () => void;
  placeholder?: string;
  className?: string;
  textareaClassName?: string;
  rows?: number;
  sendButtonAriaLabel?: string;
  disabled?: boolean;
  isSubmitting?: boolean;
  isStopping?: boolean;
  clearOnSubmit?: boolean;
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

const isTextCharacterKey = (event: KeyboardEvent) => {
  if (
    event.defaultPrevented ||
    event.ctrlKey ||
    event.metaKey ||
    event.altKey
  ) {
    return false;
  }

  if (event.isComposing) return false;

  return event.key.length === 1 && event.key !== " ";
};

const ChatInputBoxComponent = ({
  value,
  onChange,
  onSubmit,
  onStop,
  placeholder,
  className,
  textareaClassName,
  rows,
  sendButtonAriaLabel = "Nachricht senden",
  disabled = false,
  isSubmitting = false,
  isStopping = false,
  clearOnSubmit = true,
  attachments: controlledAttachments,
  onAttachmentsChange,
}: ChatInputBoxProps) => {
  // Temporarily disabled in the chat input UI. Keep attachment logic in place
  // so the feature can be re-enabled quickly without reconstructing behavior.
  const isAttachmentUiEnabled = false;

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const inputContentRef = useRef<HTMLDivElement>(null);
  const textMirrorRef = useRef<HTMLDivElement>(null);
  const textareaSelectionRef = useRef({ start: 0, end: 0 });
  const measureFrameRef = useRef<number | null>(null);
  const [isSingleLine, setIsSingleLine] = useState(true);
  const {
    attachments,
    attachmentMention,
    attachmentPopoverOpen,
    isAttachmentMentionActive,
    addAttachment,
    removeAttachment,
    setAttachments,
    setAttachmentMention,
    setAttachmentPopoverOpen,
    closeAttachmentMention: closeAttachmentMentionState,
    syncAttachmentMentionFromCursor,
  } = useChatInputAttachments({
    attachments: controlledAttachments,
    onAttachmentsChange,
  });

  const handleExternalValueChange = useCallback(() => {
    closeAttachmentMentionState();
  }, [closeAttachmentMentionState]);

  const {
    bufferedValue: draftValue,
    flushBufferedValue,
    replaceBufferedValue,
    setBufferedValue,
  } = useBufferedControlledValue({
    value,
    onChange,
    delayMs: DRAFT_SYNC_DELAY_MS,
    onExternalValueChange: handleExternalValueChange,
  });

  const hasText = draftValue.trim().length > 0;
  const hasAttachments = attachments.length > 0;
  const canSend = hasText || hasAttachments;
  const canStop = isSubmitting && !!onStop;
  const isRenderedAttachmentMentionActive =
    isAttachmentUiEnabled && isAttachmentMentionActive;

  const updateAttachmentMention = (
    nextValue: string,
    cursorPosition: number | null,
  ) => {
    syncAttachmentMentionFromCursor(nextValue, cursorPosition);
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
    const trimmed = draftValue.trim();
    if (!canSend || disabled || isSubmitting) return;

    if (!clearOnSubmit) {
      flushBufferedValue(draftValue);
    }

    onSubmit(trimmed, attachments);
    if (clearOnSubmit) {
      replaceBufferedValue("");
      onChange("");
      setAttachments([]);
      focusTextareaAt(0);
      return;
    }

    focusTextareaAt(draftValue.length);
  };

  const handleSendButtonClick = () => {
    if (canStop) {
      onStop();
      return;
    }

    submit();
  };

  const removeAttachmentMention = () => {
    if (!attachmentMention) return;

    const nextValue = `${draftValue.slice(
      0,
      attachmentMention.start,
    )}${draftValue.slice(attachmentMention.end)}`;
    const nextCursorPosition = attachmentMention.start;

    setBufferedValue(nextValue);
    closeAttachmentMentionState();

    focusTextareaAt(nextCursorPosition);
  };

  const closeAttachmentMention = () => {
    const cursorPosition = attachmentMention?.end ?? draftValue.length;

    closeAttachmentMentionState();
    focusTextareaAt(cursorPosition);
  };

  const startAttachmentMentionFromTrigger = () => {
    if (isRenderedAttachmentMentionActive) {
      closeAttachmentMention();
      return;
    }

    const textarea = textareaRef.current;
    const storedSelection = textareaSelectionRef.current;
    const selectionStart = Math.min(
      textarea?.selectionStart ?? storedSelection.start,
      draftValue.length,
    );
    const selectionEnd = Math.min(
      textarea?.selectionEnd ?? storedSelection.end,
      draftValue.length,
    );
    const characterBeforeCursor =
      selectionStart > 0 ? draftValue[selectionStart - 1] : "";
    const leadingSpace =
      characterBeforeCursor && !/\s/.test(characterBeforeCursor) ? " " : "";
    const mentionStart = selectionStart + leadingSpace.length;
    const mentionEnd = mentionStart + 1;
    const nextValue = `${draftValue.slice(
      0,
      selectionStart,
    )}${leadingSpace}@${draftValue.slice(selectionEnd)}`;

    setBufferedValue(nextValue);
    setAttachmentMention({ start: mentionStart, end: mentionEnd, query: "" });
    textareaSelectionRef.current = { start: mentionEnd, end: mentionEnd };
  };

  const syncAttachmentMentionQuery = (nextQuery: string) => {
    if (!attachmentMention) return;

    const nextEnd = attachmentMention.start + 1 + nextQuery.length;
    const nextValue = `${draftValue.slice(
      0,
      attachmentMention.start + 1,
    )}${nextQuery}${draftValue.slice(attachmentMention.end)}`;

    setBufferedValue(nextValue);
    setAttachmentMention({
      ...attachmentMention,
      end: nextEnd,
      query: nextQuery,
    });
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

  const insertTextAtCurrentSelection = useCallback(
    (text: string) => {
      const textarea = textareaRef.current;
      const storedSelection = textareaSelectionRef.current;
      const selectionStart = Math.min(
        textarea?.selectionStart ?? storedSelection.start,
        draftValue.length,
      );
      const selectionEnd = Math.min(
        textarea?.selectionEnd ?? storedSelection.end,
        draftValue.length,
      );
      const nextValue = `${draftValue.slice(0, selectionStart)}${text}${draftValue.slice(selectionEnd)}`;
      const nextCursorPosition = selectionStart + text.length;

      setBufferedValue(nextValue);
      textareaSelectionRef.current = {
        start: nextCursorPosition,
        end: nextCursorPosition,
      };
      syncAttachmentMentionFromCursor(nextValue, nextCursorPosition);
      focusTextareaAt(nextCursorPosition);
    },
    [draftValue, setBufferedValue, syncAttachmentMentionFromCursor],
  );

  const focusTextareaFromContainer = (event: MouseEvent<HTMLDivElement>) => {
    if (isInteractiveElement(event.target)) return;

    textareaRef.current?.focus();
  };

  const measureSingleLine = useCallback(() => {
    const textarea = textareaRef.current;
    const inputContent = inputContentRef.current;
    const textMirror = textMirrorRef.current;
    if (!textarea || !inputContent || !textMirror) return;

    if (measureFrameRef.current !== null) return;

    measureFrameRef.current = requestAnimationFrame(() => {
      measureFrameRef.current = null;

      const styles = window.getComputedStyle(textarea);
      const inlineTextareaWidth = Math.max(inputContent.clientWidth - 88, 0);
      textMirror.style.width = `${inlineTextareaWidth}px`;

      const lineHeight =
        Number.parseFloat(styles.lineHeight) ||
        Number.parseFloat(styles.fontSize) * 1.2;
      const singleLineHeight = Math.ceil(lineHeight);
      const nextIsSingleLine = textMirror.scrollHeight <= singleLineHeight + 1;

      setIsSingleLine((current) =>
        current === nextIsSingleLine ? current : nextIsSingleLine,
      );
    });
  }, []);

  useEffect(() => {
    const inputContent = inputContentRef.current;
    if (!inputContent) return;

    measureSingleLine();

    const resizeObserver = new ResizeObserver(measureSingleLine);
    resizeObserver.observe(inputContent);

    return () => {
      resizeObserver.disconnect();
      if (measureFrameRef.current !== null) {
        cancelAnimationFrame(measureFrameRef.current);
        measureFrameRef.current = null;
      }
    };
  }, [measureSingleLine]);

  useEffect(() => {
    measureSingleLine();
  }, [draftValue, placeholder, measureSingleLine]);

  useEffect(() => {
    const handleDocumentKeyDown = (event: KeyboardEvent) => {
      const textarea = textareaRef.current;
      if (!textarea || disabled || document.activeElement === textarea) return;
      if (isInteractiveElement(event.target)) return;
      if (!isTextCharacterKey(event)) return;

      event.preventDefault();
      insertTextAtCurrentSelection(event.key);
    };

    document.addEventListener("keydown", handleDocumentKeyDown);
    return () => {
      document.removeEventListener("keydown", handleDocumentKeyDown);
    };
  }, [disabled, insertTextAtCurrentSelection]);

  return (
    <div
      onClick={focusTextareaFromContainer}
      className={cn(
        "overflow-hidden rounded-2xl bg-card/55 px-5 py-3 backdrop-blur-md sm:px-4 sm:py-3 cursor-text",
        className,
      )}
    >
      {isAttachmentUiEnabled && (
        <AttachmentList
          attachments={attachments}
          onRemove={disabled || isSubmitting ? undefined : removeAttachment}
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
          {(draftValue || placeholder || " ").endsWith("\n")
            ? `${draftValue || placeholder || " "}\n `
            : draftValue || placeholder || " "}
        </div>

        <Textarea
          ref={textareaRef}
          rows={rows ?? 1}
          value={draftValue}
          disabled={disabled}
          onChange={(e) => {
            rememberTextareaSelection(e.target);
            setBufferedValue(e.target.value);
            updateAttachmentMention(e.target.value, e.target.selectionStart);
          }}
          onSelect={(e) => {
            rememberTextareaSelection(e.currentTarget);
            updateAttachmentMention(
              e.currentTarget.value,
              e.currentTarget.selectionStart,
            );
          }}
          onBlur={() => flushBufferedValue()}
          onKeyDown={(e) => {
            if (isRenderedAttachmentMentionActive) {
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
            isSingleLine ? "shrink-0" : "justify-end",
          )}
        >
          {isAttachmentUiEnabled && (
            <AttachmentPopover
              attachments={attachments}
              onAdd={addAttachment}
              disabled={disabled || isSubmitting}
              open={attachmentPopoverOpen}
              onOpenChange={handleAttachmentPopoverOpenChange}
              query={attachmentMention?.query ?? ""}
              onQueryChange={syncAttachmentMentionQuery}
              onTriggerClick={startAttachmentMentionFromTrigger}
              hideSearchInput={isRenderedAttachmentMentionActive}
              onPick={removeAttachmentMention}
            />
          )}
          <SendButton
            onClick={handleSendButtonClick}
            disabled={
              disabled || (isSubmitting && !canStop) || (!canStop && !canSend)
            }
            isLoading={isSubmitting}
            isStopMode={canStop}
            isStopping={isStopping}
            ariaLabel={canStop ? "Antwort stoppen" : sendButtonAriaLabel}
          />
        </div>
      </div>
    </div>
  );
};

ChatInputBoxComponent.displayName = "ChatInputBox";

export const ChatInputBox = memo(ChatInputBoxComponent);

import {
  createContext,
  memo,
  type ComponentProps,
  type MouseEvent,
  type ReactNode,
  type RefObject,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";

import { AttachmentList } from "@/features/chat/components/attachments/attachment-list";
import { AttachmentPopover } from "@/features/chat/components/attachments/attachment-popover";
import type { ChatAttachment } from "@/features/chat/components/attachments/attachment-types";
import { SendButton } from "@/features/chat/components/send-button";
import { useChatInputAttachments } from "@/features/chat/hooks/use-chat-input-attachments";
import { Textarea } from "@/shared/ui/textarea";
import { useBufferedControlledValue } from "@/shared/hooks/useBufferedControlledValue";
import { cn } from "@/shared/lib/utils";

const DRAFT_SYNC_DELAY_MS = 180;

type ChatInputBoxProps = {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (
    text: string,
    attachments: ChatAttachment[],
  ) => void | Promise<void>;
  children?: ReactNode;
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

type ChatInputContextValue = {
  textareaRef: RefObject<HTMLTextAreaElement | null>;
  inputContentRef: RefObject<HTMLDivElement | null>;
  textMirrorRef: RefObject<HTMLDivElement | null>;
  text: string;
  setText: (value: string) => void;
  flushText: () => void;
  submit: () => void;
  handleSendButtonClick: () => void;
  handleTextareaChange: ComponentProps<typeof Textarea>["onChange"];
  handleTextareaSelect: ComponentProps<typeof Textarea>["onSelect"];
  handleTextareaKeyDown: ComponentProps<typeof Textarea>["onKeyDown"];
  focusTextareaFromContainer: (event: MouseEvent<HTMLDivElement>) => void;
  attachments: ChatAttachment[];
  addAttachment: (attachment: ChatAttachment) => void;
  removeAttachment: (attachment: ChatAttachment) => void;
  attachmentPopoverOpen: boolean;
  setAttachmentPopoverOpen: (open: boolean) => void;
  attachmentQuery: string;
  syncAttachmentMentionQuery: (query: string) => void;
  startAttachmentMentionFromTrigger: () => void;
  removeAttachmentMention: () => void;
  isAttachmentUiEnabled: boolean;
  isAttachmentMentionActive: boolean;
  isSingleLine: boolean;
  canSend: boolean;
  canStop: boolean;
  disabled: boolean;
  isSubmitting: boolean;
  isStopping: boolean;
  placeholder?: string;
  textareaClassName?: string;
  rows?: number;
  sendButtonAriaLabel: string;
};

type ChatInputTextAreaProps = Omit<
  ComponentProps<typeof Textarea>,
  | "ref"
  | "rows"
  | "value"
  | "disabled"
  | "onChange"
  | "onSelect"
  | "onBlur"
  | "onKeyDown"
  | "placeholder"
>;

type ChatInputContentProps = {
  children?: ReactNode;
  className?: string;
};

type ChatInputToolbarProps = {
  children: ReactNode;
  className?: string;
};

type ChatInputAddAttachmentProps = {
  className?: string;
};

type ChatInputSubmitProps = {
  className?: string;
};

type ChatInputBoxCompound = typeof ChatInputBoxComponent & {
  PreviewList: typeof ChatInputPreviewList;
  Content: typeof ChatInputContent;
  TextArea: typeof ChatInputTextArea;
  Toolbar: typeof ChatInputToolbar;
  AddAttachment: typeof ChatInputAddAttachment;
  Submit: typeof ChatInputSubmit;
};

const ChatInputContext = createContext<ChatInputContextValue | null>(null);

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

const useChatInput = () => {
  const context = useContext(ChatInputContext);
  if (!context) {
    throw new Error("ChatInputBox subcomponents must be used inside ChatInputBox.");
  }

  return context;
};

const ChatInputPreviewList = () => {
  const {
    attachments,
    disabled,
    isAttachmentUiEnabled,
    isSubmitting,
    removeAttachment,
  } = useChatInput();

  if (!isAttachmentUiEnabled) return null;

  return (
    <AttachmentList
      attachments={attachments}
      onRemove={disabled || isSubmitting ? undefined : removeAttachment}
    />
  );
};

const ChatInputContent = ({ children, className }: ChatInputContentProps) => {
  const {
    inputContentRef,
    isSingleLine,
    placeholder,
    text,
    textMirrorRef,
  } = useChatInput();

  return (
    <div
      ref={inputContentRef}
      className={cn(
        isSingleLine
          ? "relative flex items-center gap-2"
          : "relative flex flex-col gap-3",
        className,
      )}
    >
      <div
        ref={textMirrorRef}
        aria-hidden="true"
        className="pointer-events-none absolute -z-10 whitespace-pre-wrap break-words p-0 text-base opacity-0 md:text-base"
      >
        {(text || placeholder || " ").endsWith("\n")
          ? `${text || placeholder || " "}\n `
          : text || placeholder || " "}
      </div>

      {children ?? (
        <>
          <ChatInputTextArea />
          <ChatInputToolbar>
            <ChatInputAddAttachment />
            <ChatInputSubmit />
          </ChatInputToolbar>
        </>
      )}
    </div>
  );
};

const ChatInputTextArea = ({
  className,
  ...props
}: ChatInputTextAreaProps) => {
  const {
    disabled,
    flushText,
    handleTextareaChange,
    handleTextareaKeyDown,
    handleTextareaSelect,
    isSingleLine,
    placeholder,
    rows,
    text,
    textareaClassName,
    textareaRef,
  } = useChatInput();

  return (
    <Textarea
      ref={textareaRef}
      rows={rows ?? 1}
      value={text}
      disabled={disabled}
      onChange={handleTextareaChange}
      onSelect={handleTextareaSelect}
      onBlur={() => flushText()}
      onKeyDown={handleTextareaKeyDown}
      placeholder={placeholder}
      className={cn(
        "max-h-72 min-h-9 flex-1 resize-none border-none bg-transparent p-0 pt-0.5 text-base shadow-none focus-visible:ring-0 md:text-base",
        !isSingleLine && "min-h-15",
        textareaClassName,
        className,
      )}
      {...props}
    />
  );
};

const ChatInputToolbar = ({ children, className }: ChatInputToolbarProps) => {
  const { isSingleLine } = useChatInput();

  return (
    <div
      className={cn(
        "flex items-center gap-1.5",
        isSingleLine ? "shrink-0" : "justify-end",
        className,
      )}
    >
      {children}
    </div>
  );
};

const ChatInputAddAttachment = ({ className }: ChatInputAddAttachmentProps) => {
  const {
    addAttachment,
    attachmentPopoverOpen,
    attachmentQuery,
    attachments,
    disabled,
    isAttachmentMentionActive,
    isAttachmentUiEnabled,
    isSubmitting,
    removeAttachmentMention,
    setAttachmentPopoverOpen,
    startAttachmentMentionFromTrigger,
    syncAttachmentMentionQuery,
  } = useChatInput();

  if (!isAttachmentUiEnabled) return null;

  return (
    <AttachmentPopover
      attachments={attachments}
      onAdd={addAttachment}
      disabled={disabled || isSubmitting}
      open={attachmentPopoverOpen}
      onOpenChange={setAttachmentPopoverOpen}
      query={attachmentQuery}
      onQueryChange={syncAttachmentMentionQuery}
      onTriggerClick={startAttachmentMentionFromTrigger}
      hideSearchInput={isAttachmentMentionActive}
      onPick={removeAttachmentMention}
      triggerClassName={className}
    />
  );
};

const ChatInputSubmit = ({ className }: ChatInputSubmitProps) => {
  const {
    canSend,
    canStop,
    disabled,
    handleSendButtonClick,
    isStopping,
    isSubmitting,
    sendButtonAriaLabel,
  } = useChatInput();

  return (
    <SendButton
      onClick={handleSendButtonClick}
      disabled={disabled || (isSubmitting && !canStop) || (!canStop && !canSend)}
      isLoading={isSubmitting}
      isStopMode={canStop}
      isStopping={isStopping}
      ariaLabel={canStop ? "Antwort stoppen" : sendButtonAriaLabel}
      className={className}
    />
  );
};

const ChatInputBoxDefault = () => (
  <>
    <ChatInputPreviewList />
    <ChatInputContent>
      <ChatInputTextArea />
      <ChatInputToolbar>
        <ChatInputAddAttachment />
        <ChatInputSubmit />
      </ChatInputToolbar>
    </ChatInputContent>
  </>
);

const ChatInputBoxComponent = ({
  value,
  onChange,
  onSubmit,
  children,
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

  const updateAttachmentMention = useCallback(
    (nextValue: string, cursorPosition: number | null) => {
      syncAttachmentMentionFromCursor(nextValue, cursorPosition);
    },
    [syncAttachmentMentionFromCursor],
  );

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

  const submit = useCallback(() => {
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
  }, [
    attachments,
    canSend,
    clearOnSubmit,
    disabled,
    draftValue,
    flushBufferedValue,
    isSubmitting,
    onChange,
    onSubmit,
    replaceBufferedValue,
    setAttachments,
  ]);

  const handleSendButtonClick = useCallback(() => {
    if (canStop) {
      onStop?.();
      return;
    }

    submit();
  }, [canStop, onStop, submit]);

  const removeAttachmentMention = useCallback(() => {
    if (!attachmentMention) return;

    const nextValue = `${draftValue.slice(
      0,
      attachmentMention.start,
    )}${draftValue.slice(attachmentMention.end)}`;
    const nextCursorPosition = attachmentMention.start;

    setBufferedValue(nextValue);
    closeAttachmentMentionState();

    focusTextareaAt(nextCursorPosition);
  }, [
    attachmentMention,
    closeAttachmentMentionState,
    draftValue,
    setBufferedValue,
  ]);

  const closeAttachmentMention = useCallback(() => {
    const cursorPosition = attachmentMention?.end ?? draftValue.length;

    closeAttachmentMentionState();
    focusTextareaAt(cursorPosition);
  }, [attachmentMention?.end, closeAttachmentMentionState, draftValue.length]);

  const startAttachmentMentionFromTrigger = useCallback(() => {
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
  }, [
    closeAttachmentMention,
    draftValue,
    isRenderedAttachmentMentionActive,
    setAttachmentMention,
    setBufferedValue,
  ]);

  const syncAttachmentMentionQuery = useCallback(
    (nextQuery: string) => {
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
    },
    [attachmentMention, draftValue, setAttachmentMention, setBufferedValue],
  );

  const handleAttachmentPopoverOpenChange = useCallback(
    (nextOpen: boolean) => {
      if (nextOpen) {
        if (attachmentMention) {
          setAttachmentPopoverOpen(true);
        }
        return;
      }

      closeAttachmentMention();
    },
    [attachmentMention, closeAttachmentMention, setAttachmentPopoverOpen],
  );

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

  const focusTextareaFromContainer = useCallback(
    (event: MouseEvent<HTMLDivElement>) => {
      if (isInteractiveElement(event.target)) return;

      textareaRef.current?.focus();
    },
    [],
  );

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

  const handleTextareaChange: ChatInputContextValue["handleTextareaChange"] = (
    e,
  ) => {
    rememberTextareaSelection(e.target);
    setBufferedValue(e.target.value);
    updateAttachmentMention(e.target.value, e.target.selectionStart);
  };

  const handleTextareaSelect: ChatInputContextValue["handleTextareaSelect"] = (
    e,
  ) => {
    rememberTextareaSelection(e.currentTarget);
    updateAttachmentMention(
      e.currentTarget.value,
      e.currentTarget.selectionStart,
    );
  };

  const handleTextareaKeyDown: ChatInputContextValue["handleTextareaKeyDown"] = (
    e,
  ) => {
    if (isRenderedAttachmentMentionActive) {
      if (e.key === "ArrowDown" || e.key === "ArrowUp" || e.key === "Enter") {
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
  };

  const contextValue: ChatInputContextValue = {
    textareaRef,
    inputContentRef,
    textMirrorRef,
    text: draftValue,
    setText: setBufferedValue,
    flushText: flushBufferedValue,
    submit,
    handleSendButtonClick,
    handleTextareaChange,
    handleTextareaSelect,
    handleTextareaKeyDown,
    focusTextareaFromContainer,
    attachments,
    addAttachment,
    removeAttachment,
    attachmentPopoverOpen,
    setAttachmentPopoverOpen: handleAttachmentPopoverOpenChange,
    attachmentQuery: attachmentMention?.query ?? "",
    syncAttachmentMentionQuery,
    startAttachmentMentionFromTrigger,
    removeAttachmentMention,
    isAttachmentUiEnabled,
    isAttachmentMentionActive: isRenderedAttachmentMentionActive,
    isSingleLine,
    canSend,
    canStop,
    disabled,
    isSubmitting,
    isStopping,
    placeholder,
    textareaClassName,
    rows,
    sendButtonAriaLabel,
  };

  return (
    <ChatInputContext.Provider value={contextValue}>
      <div
        onClick={focusTextareaFromContainer}
        className={cn(
          "cursor-text overflow-hidden rounded-2xl bg-card/55 px-5 py-3 backdrop-blur-md sm:px-4 sm:py-3",
          className,
        )}
      >
        {children ?? <ChatInputBoxDefault />}
      </div>
    </ChatInputContext.Provider>
  );
};

ChatInputBoxComponent.displayName = "ChatInputBox";
ChatInputPreviewList.displayName = "ChatInputBox.PreviewList";
ChatInputContent.displayName = "ChatInputBox.Content";
ChatInputTextArea.displayName = "ChatInputBox.TextArea";
ChatInputToolbar.displayName = "ChatInputBox.Toolbar";
ChatInputAddAttachment.displayName = "ChatInputBox.AddAttachment";
ChatInputSubmit.displayName = "ChatInputBox.Submit";

export const ChatInputBox = memo(
  ChatInputBoxComponent,
) as unknown as ChatInputBoxCompound;

ChatInputBox.PreviewList = ChatInputPreviewList;
ChatInputBox.Content = ChatInputContent;
ChatInputBox.TextArea = ChatInputTextArea;
ChatInputBox.Toolbar = ChatInputToolbar;
ChatInputBox.AddAttachment = ChatInputAddAttachment;
ChatInputBox.Submit = ChatInputSubmit;

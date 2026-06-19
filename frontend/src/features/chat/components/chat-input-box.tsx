import {
  createContext,
  memo,
  type ClipboardEvent,
  type ChangeEvent,
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

import { Plus } from "lucide-react";

import { AttachmentList } from "@/features/chat/components/attachments/attachment-list";
import { AttachmentPopover } from "@/features/chat/components/attachments/attachment-popover";
import type { ChatAttachment } from "@/features/chat/components/attachments/attachment-types";
import { ModelSelect } from "@/features/chat/components/model-select";
import { SendButton } from "@/features/chat/components/send-button";
import { TranscriptionButton } from "@/features/chat/components/transcription-button";
import { TranscriptionWaveform } from "@/features/chat/components/transcription-waveform";
import { uploadSessionImageFile } from "@/features/chat/api/image-attachments";
import { useChatInputAttachments } from "@/features/chat/hooks/use-chat-input-attachments";
import { useRealtimeTranscription } from "@/features/chat/hooks/useRealtimeTranscription";
import {
  playTranscriptionStartSound,
  playTranscriptionStopSound,
} from "@/features/chat/lib/transcription-sounds";
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
  imageUploadSessionId?: string;
  selectedModel?: string;
  onModelChange?: (modelId: string) => void;
};

type ChatInputContextValue = {
  textareaRef: RefObject<HTMLTextAreaElement | null>;
  text: string;
  setText: (value: string) => void;
  flushText: () => void;
  submit: () => void;
  handleSendButtonClick: () => void;
  handleTextareaChange: ComponentProps<typeof Textarea>["onChange"];
  handleTextareaPaste: ComponentProps<typeof Textarea>["onPaste"];
  handleTextareaSelect: ComponentProps<typeof Textarea>["onSelect"];
  handleTextareaKeyDown: ComponentProps<typeof Textarea>["onKeyDown"];
  focusTextareaFromContainer: (event: MouseEvent<HTMLDivElement>) => void;
  attachments: ChatAttachment[];
  addAttachment: (attachment: ChatAttachment) => void;
  addImageFiles: (files: File[]) => void;
  removeAttachment: (attachment: ChatAttachment) => void;
  isUploadingAttachments: boolean;
  hasFailedAttachmentUpload: boolean;
  attachmentPopoverOpen: boolean;
  setAttachmentPopoverOpen: (open: boolean) => void;
  attachmentQuery: string;
  syncAttachmentMentionQuery: (query: string) => void;
  startAttachmentMentionFromTrigger: () => void;
  removeAttachmentMention: () => void;
  isAttachmentUiEnabled: boolean;
  isAttachmentMentionActive: boolean;
  canSend: boolean;
  canStop: boolean;
  disabled: boolean;
  isSubmitting: boolean;
  isStopping: boolean;
  isTranscribing: boolean;
  isTranscriptionStarting: boolean;
  transcriptionAnalyser: AnalyserNode | null;
  toggleTranscription: () => void;
  selectedModel?: string;
  onModelChange?: (modelId: string) => void;
  placeholder?: string;
  textareaClassName?: string;
  rows?: number;
  sendButtonAriaLabel: string;
  openFilePicker: () => void;
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
  | "onPaste"
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

type ChatInputModelSelectProps = {
  className?: string;
};

type ChatInputAddButtonProps = {
  className?: string;
  onClick?: () => void;
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
  Waveform: typeof ChatInputWaveform;
  Toolbar: typeof ChatInputToolbar;
  ModelSelect: typeof ChatInputModelSelect;
  AddButton: typeof ChatInputAddButton;
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

const isImageFile = (file: File) => file.type.startsWith("image/");

const formatFileSize = (bytes: number) => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

const createImageAttachment = (file: File): ChatAttachment => {
  const namedFile =
    file.name.trim().length > 0
      ? file
      : new File([file], `clipboard-${Date.now()}.png`, {
          type: file.type || "image/png",
          lastModified: file.lastModified,
        });

  return {
    id: crypto.randomUUID(),
    kind: "image",
    title: namedFile.name,
    subtitle: formatFileSize(namedFile.size),
    imageUrl: URL.createObjectURL(namedFile),
    file: namedFile,
    contentType: namedFile.type,
    sizeBytes: namedFile.size,
  };
};

const revokeAttachmentPreview = (attachment: ChatAttachment) => {
  if (attachment.kind !== "image" || !attachment.imageUrl) return;
  if (!attachment.imageUrl.startsWith("blob:")) return;

  URL.revokeObjectURL(attachment.imageUrl);
};

const useChatInput = () => {
  const context = useContext(ChatInputContext);
  if (!context) {
    throw new Error(
      "ChatInputBox subcomponents must be used inside ChatInputBox.",
    );
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
  return (
    <div className={cn("relative flex flex-col gap-3", className)}>
      {children ?? (
        <>
          <ChatInputTextArea />
          <ChatInputWaveform />
          <ChatInputToolbar className="-mx-1">
            <ChatInputAddButton />
            <div className="ml-auto flex items-center gap-2">
              <ChatInputModelSelect />
              <ChatInputSubmit />
            </div>
          </ChatInputToolbar>
        </>
      )}
    </div>
  );
};

const ChatInputTextArea = ({ className, ...props }: ChatInputTextAreaProps) => {
  const {
    disabled,
    flushText,
    handleTextareaChange,
    handleTextareaKeyDown,
    handleTextareaPaste,
    handleTextareaSelect,
    isTranscriptionStarting,
    placeholder,
    rows,
    text,
    textareaClassName,
    textareaRef,
  } = useChatInput();

  const effectivePlaceholder = isTranscriptionStarting
    ? "Mikrofon wird verbunden …"
    : placeholder;

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
      onPaste={handleTextareaPaste}
      placeholder={effectivePlaceholder}
      className={cn(
        "max-h-72 min-h-10 flex-1 resize-none border-none bg-transparent p-0 pt-0.5 text-base shadow-none focus-visible:ring-0 md:text-base",
        textareaClassName,
        className,
      )}
      {...props}
    />
  );
};

const ChatInputWaveform = ({ className }: { className?: string }) => {
  const { isTranscribing, isTranscriptionStarting, transcriptionAnalyser } =
    useChatInput();

  if (!isTranscribing && !isTranscriptionStarting) return null;

  return (
    <TranscriptionWaveform
      analyser={transcriptionAnalyser}
      active={isTranscribing}
      connecting={isTranscriptionStarting}
      className={className}
    />
  );
};

const ChatInputToolbar = ({ children, className }: ChatInputToolbarProps) => {
  return (
    <div className={cn("flex items-center gap-1.5", className)}>{children}</div>
  );
};

const ChatInputAddButton = ({
  className,
  onClick,
}: ChatInputAddButtonProps) => {
  const {
    addAttachment,
    attachments,
    disabled,
    isAttachmentUiEnabled,
    isSubmitting,
    openFilePicker,
  } = useChatInput();
  const [open, setOpen] = useState(false);

  if (!isAttachmentUiEnabled) return null;

  return (
    <AttachmentPopover
      attachments={attachments}
      onAdd={addAttachment}
      disabled={disabled || isSubmitting}
      open={open}
      onOpenChange={setOpen}
      showActionMenu
      onUploadClick={onClick ?? openFilePicker}
      triggerIcon={<Plus className="size-5" />}
      triggerAriaLabel="Dateien oder Spotify hinzufuegen"
      triggerClassName={cn("size-9", className)}
    />
  );
};

const ChatInputModelSelect = ({ className }: ChatInputModelSelectProps) => {
  const { disabled, isSubmitting, onModelChange, selectedModel } =
    useChatInput();

  return (
    <ModelSelect
      value={selectedModel}
      onChange={onModelChange}
      disabled={disabled || isSubmitting}
      className={className}
    />
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
    isTranscribing,
    isTranscriptionStarting,
    sendButtonAriaLabel,
    toggleTranscription,
  } = useChatInput();

  const showTranscription =
    !canStop && (isTranscribing || isTranscriptionStarting || !canSend);

  if (showTranscription) {
    return (
      <TranscriptionButton
        isRecording={isTranscribing}
        isStarting={isTranscriptionStarting}
        disabled={disabled || isSubmitting}
        onClick={toggleTranscription}
        className={className}
      />
    );
  }

  return (
    <SendButton
      onClick={handleSendButtonClick}
      disabled={
        disabled || (isSubmitting && !canStop) || (!canStop && !canSend)
      }
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
      <ChatInputWaveform />
      <ChatInputToolbar className="-mx-1">
        <ChatInputAddButton />
        <div className="ml-auto flex items-center gap-2">
          <ChatInputModelSelect />
          <ChatInputSubmit />
        </div>
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
  imageUploadSessionId,
  selectedModel,
  onModelChange,
}: ChatInputBoxProps) => {
  const isAttachmentUiEnabled = true;

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const attachmentsRef = useRef<ChatAttachment[]>([]);
  const uploadControllersRef = useRef(new Map<string, AbortController>());
  const textareaSelectionRef = useRef({ start: 0, end: 0 });
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
  const isUploadingAttachments = attachments.some(
    (attachment) => attachment.uploadStatus === "uploading",
  );
  const hasFailedAttachmentUpload = attachments.some(
    (attachment) => attachment.uploadStatus === "failed",
  );
  const canSend =
    (hasText || hasAttachments) &&
    !isUploadingAttachments &&
    !hasFailedAttachmentUpload;
  const canStop = isSubmitting && !!onStop;
  const isRenderedAttachmentMentionActive =
    isAttachmentUiEnabled && isAttachmentMentionActive;

  useEffect(() => {
    attachmentsRef.current = attachments;
  }, [attachments]);

  useEffect(
    () => () => {
      uploadControllersRef.current.forEach((controller) => controller.abort());
      attachmentsRef.current.forEach(revokeAttachmentPreview);
    },
    [],
  );

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
      attachments.forEach(revokeAttachmentPreview);
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

  const updateAttachmentById = useCallback(
    (
      attachmentId: string,
      update: (attachment: ChatAttachment) => ChatAttachment,
    ) => {
      const nextAttachments = attachmentsRef.current.map((attachment) =>
        attachment.id === attachmentId ? update(attachment) : attachment,
      );

      attachmentsRef.current = nextAttachments;
      setAttachments(nextAttachments);
    },
    [setAttachments],
  );

  const startImageUpload = useCallback(
    (attachment: ChatAttachment) => {
      if (
        !imageUploadSessionId ||
        attachment.kind !== "image" ||
        !attachment.file
      ) {
        return;
      }

      const controller = new AbortController();
      uploadControllersRef.current.set(attachment.id, controller);

      void uploadSessionImageFile(
        imageUploadSessionId,
        attachment.file,
        controller.signal,
      )
        .then((image) => {
          uploadControllersRef.current.delete(attachment.id);
          if (controller.signal.aborted) return;

          updateAttachmentById(attachment.id, (current) => ({
            ...current,
            id: image.id,
            storageKey: image.storageKey,
            contentType: image.contentType,
            sizeBytes: image.sizeBytes,
            uploadStatus: "uploaded",
            uploadError: undefined,
          }));
        })
        .catch((error) => {
          uploadControllersRef.current.delete(attachment.id);
          if (controller.signal.aborted) return;

          updateAttachmentById(attachment.id, (current) => ({
            ...current,
            uploadStatus: "failed",
            uploadError:
              error instanceof Error
                ? error.message
                : "Bild konnte nicht hochgeladen werden.",
          }));
        });
    },
    [imageUploadSessionId, updateAttachmentById],
  );

  const addImageFiles = useCallback(
    (files: File[]) => {
      const imageFiles = files.filter(isImageFile);
      if (imageFiles.length === 0) return;
      const imageAttachments = imageFiles.map((file) => {
        const attachment = createImageAttachment(file);
        return imageUploadSessionId
          ? { ...attachment, uploadStatus: "uploading" as const }
          : attachment;
      });

      const nextAttachments = [...attachmentsRef.current, ...imageAttachments];
      attachmentsRef.current = nextAttachments;
      setAttachments(nextAttachments);
      imageAttachments.forEach(startImageUpload);
    },
    [imageUploadSessionId, setAttachments, startImageUpload],
  );

  const openFilePicker = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleFileInputChange = useCallback(
    (event: ChangeEvent<HTMLInputElement>) => {
      addImageFiles(Array.from(event.currentTarget.files ?? []));
      event.currentTarget.value = "";
    },
    [addImageFiles],
  );

  const handleTextareaPaste = useCallback(
    (event: ClipboardEvent<HTMLTextAreaElement>) => {
      const files = Array.from(event.clipboardData.files).filter(isImageFile);
      if (files.length === 0) return;

      event.preventDefault();
      addImageFiles(files);
    },
    [addImageFiles],
  );

  const removeAttachmentAndPreview = useCallback(
    (attachment: ChatAttachment) => {
      uploadControllersRef.current.get(attachment.id)?.abort();
      uploadControllersRef.current.delete(attachment.id);
      revokeAttachmentPreview(attachment);
      removeAttachment(attachment);
    },
    [removeAttachment],
  );

  const handleSendButtonClick = useCallback(() => {
    if (canStop) {
      onStop?.();
      return;
    }

    submit();
  }, [canStop, onStop, submit]);

  const {
    isRecording: isTranscribing,
    isStarting: isTranscriptionStarting,
    analyser: transcriptionAnalyser,
    start: startTranscription,
    stop: stopTranscription,
  } = useRealtimeTranscription({
    value: draftValue,
    onTranscriptChange: setBufferedValue,
    disabled,
  });

  const toggleTranscription = useCallback(() => {
    if (isTranscribing || isTranscriptionStarting) {
      playTranscriptionStopSound();
      void stopTranscription();
      return;
    }

    playTranscriptionStartSound();
    void startTranscription();
  }, [
    isTranscribing,
    isTranscriptionStarting,
    startTranscription,
    stopTranscription,
  ]);

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

  const handleTextareaKeyDown: ChatInputContextValue["handleTextareaKeyDown"] =
    (e) => {
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
    text: draftValue,
    setText: setBufferedValue,
    flushText: flushBufferedValue,
    submit,
    handleSendButtonClick,
    handleTextareaChange,
    handleTextareaPaste,
    handleTextareaSelect,
    handleTextareaKeyDown,
    focusTextareaFromContainer,
    attachments,
    addAttachment,
    addImageFiles,
    removeAttachment: removeAttachmentAndPreview,
    isUploadingAttachments,
    hasFailedAttachmentUpload,
    attachmentPopoverOpen,
    setAttachmentPopoverOpen: handleAttachmentPopoverOpenChange,
    attachmentQuery: attachmentMention?.query ?? "",
    syncAttachmentMentionQuery,
    startAttachmentMentionFromTrigger,
    removeAttachmentMention,
    isAttachmentUiEnabled,
    isAttachmentMentionActive: isRenderedAttachmentMentionActive,
    canSend,
    canStop,
    disabled,
    isSubmitting,
    isStopping,
    isTranscribing,
    isTranscriptionStarting,
    transcriptionAnalyser,
    toggleTranscription,
    selectedModel,
    onModelChange,
    placeholder,
    textareaClassName,
    rows,
    sendButtonAriaLabel,
    openFilePicker,
  };

  return (
    <ChatInputContext.Provider value={contextValue}>
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        multiple
        className="hidden"
        onChange={handleFileInputChange}
        tabIndex={-1}
      />
      <div
        onClick={focusTextareaFromContainer}
        className={cn(
          "cursor-text overflow-hidden rounded-2xl bg-card/55 px-5 py-3 backdrop-blur-md sm:px-5 sm:py-4",
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
ChatInputWaveform.displayName = "ChatInputBox.Waveform";
ChatInputToolbar.displayName = "ChatInputBox.Toolbar";
ChatInputModelSelect.displayName = "ChatInputBox.ModelSelect";
ChatInputAddButton.displayName = "ChatInputBox.AddButton";
ChatInputAddAttachment.displayName = "ChatInputBox.AddAttachment";
ChatInputSubmit.displayName = "ChatInputBox.Submit";

export const ChatInputBox = memo(
  ChatInputBoxComponent,
) as unknown as ChatInputBoxCompound;

ChatInputBox.PreviewList = ChatInputPreviewList;
ChatInputBox.Content = ChatInputContent;
ChatInputBox.TextArea = ChatInputTextArea;
ChatInputBox.Waveform = ChatInputWaveform;
ChatInputBox.Toolbar = ChatInputToolbar;
ChatInputBox.ModelSelect = ChatInputModelSelect;
ChatInputBox.AddButton = ChatInputAddButton;
ChatInputBox.AddAttachment = ChatInputAddAttachment;
ChatInputBox.Submit = ChatInputSubmit;

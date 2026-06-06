import { useCallback, useReducer } from "react";

import type { ChatAttachment } from "@/features/chat/components/attachments/attachment-types";

export type AttachmentMention = {
  start: number;
  end: number;
  query: string;
};

type ChatInputAttachmentState = {
  attachmentPopoverOpen: boolean;
  attachmentMention: AttachmentMention | null;
  internalAttachments: ChatAttachment[];
};

type ChatInputAttachmentAction =
  | {
      type: "attachments:set";
      attachments: ChatAttachment[];
    }
  | {
      type: "mention:set";
      mention: AttachmentMention | null;
    }
  | {
      type: "mention:clear";
    }
  | {
      type: "popover:set";
      open: boolean;
    };

type UseChatInputAttachmentsArgs = {
  attachments?: ChatAttachment[];
  onAttachmentsChange?: (attachments: ChatAttachment[]) => void;
};

const initialState: ChatInputAttachmentState = {
  attachmentPopoverOpen: false,
  attachmentMention: null,
  internalAttachments: [],
};

const chatInputAttachmentReducer = (
  state: ChatInputAttachmentState,
  action: ChatInputAttachmentAction,
): ChatInputAttachmentState => {
  switch (action.type) {
    case "attachments:set":
      return {
        ...state,
        internalAttachments: action.attachments,
      };
    case "mention:set":
      return {
        ...state,
        attachmentMention: action.mention,
        attachmentPopoverOpen: action.mention !== null,
      };
    case "mention:clear":
      return {
        ...state,
        attachmentMention: null,
        attachmentPopoverOpen: false,
      };
    case "popover:set":
      return {
        ...state,
        attachmentPopoverOpen: action.open,
      };
  }
};

const attachmentKey = (attachment: ChatAttachment) =>
  `${attachment.kind}:${attachment.id}`;

export const findAttachmentMention = (
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

export const useChatInputAttachments = ({
  attachments: controlledAttachments,
  onAttachmentsChange,
}: UseChatInputAttachmentsArgs) => {
  const [state, dispatch] = useReducer(
    chatInputAttachmentReducer,
    initialState,
  );
  const attachments = controlledAttachments ?? state.internalAttachments;

  const setAttachments = useCallback(
    (nextAttachments: ChatAttachment[]) => {
      if (controlledAttachments === undefined) {
        dispatch({
          type: "attachments:set",
          attachments: nextAttachments,
        });
      }

      onAttachmentsChange?.(nextAttachments);
    },
    [controlledAttachments, onAttachmentsChange],
  );

  const addAttachment = useCallback(
    (attachment: ChatAttachment) => {
      const key = attachmentKey(attachment);
      if (attachments.some((existing) => attachmentKey(existing) === key)) {
        return;
      }

      setAttachments([...attachments, attachment]);
    },
    [attachments, setAttachments],
  );

  const removeAttachment = useCallback(
    (attachment: ChatAttachment) => {
      const key = attachmentKey(attachment);
      setAttachments(
        attachments.filter((existing) => attachmentKey(existing) !== key),
      );
    },
    [attachments, setAttachments],
  );

  const setAttachmentMention = useCallback(
    (mention: AttachmentMention | null) => {
      dispatch({ type: "mention:set", mention });
    },
    [],
  );

  const syncAttachmentMentionFromCursor = useCallback(
    (nextValue: string, cursorPosition: number | null) => {
      if (cursorPosition === null) return;

      dispatch({
        type: "mention:set",
        mention: findAttachmentMention(nextValue, cursorPosition),
      });
    },
    [],
  );

  const closeAttachmentMention = useCallback(() => {
    dispatch({ type: "mention:clear" });
  }, []);

  const setAttachmentPopoverOpen = useCallback((open: boolean) => {
    dispatch({ type: "popover:set", open });
  }, []);

  return {
    attachments,
    attachmentMention: state.attachmentMention,
    attachmentPopoverOpen: state.attachmentPopoverOpen,
    isAttachmentMentionActive:
      state.attachmentPopoverOpen && state.attachmentMention !== null,
    addAttachment,
    removeAttachment,
    setAttachments,
    setAttachmentMention,
    setAttachmentPopoverOpen,
    closeAttachmentMention,
    syncAttachmentMentionFromCursor,
  };
};

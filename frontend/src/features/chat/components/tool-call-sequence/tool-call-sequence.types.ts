import type {
  ToolCallActionType,
  ToolCallItem,
  ToolCallStatus,
} from "@/features/chat/types";

export type { ToolCallActionType, ToolCallItem, ToolCallStatus };

export type ToolCallAccordionProps = {
  calls: ToolCallItem[];
  className?: string;
  defaultOpen?: boolean;
};

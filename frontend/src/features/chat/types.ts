export type ToolCallStatus = "pending" | "running" | "completed" | "failed";
export type ToolCallActionType = "search" | "fetch" | "mutate";

export type ToolCallItem = {
  id: string;
  text: string;
  status?: ToolCallStatus;
  actionType?: ToolCallActionType | string | null;
  detail?: string;
};

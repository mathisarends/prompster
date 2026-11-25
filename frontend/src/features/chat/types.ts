export type ToolCallStatus = "pending" | "running" | "completed" | "failed";
export type ToolCallActionType =
  | "ask_onboarding_question"
  | "search_tracks"
  | "search_playlists"
  | "add_deck_tracks"
  | "remove_deck_tracks"
  | "replace_deck_tracks"
  | "get_spotify_playlist_tracks"
  | "self_review";

export type ToolCallRetry = {
  attempt: number;
  maxAttempts: number;
};

export type ToolCallItem = {
  id: string;
  text: string;
  status?: ToolCallStatus;
  actionType?: ToolCallActionType | string | null;
  detail?: string;
  retry?: ToolCallRetry | null;
  resultItems?: {
    title: string;
    coverUrl?: string | null;
    artist?: string | null;
    trackUri?: string | null;
  }[];
};

export type ToolCallSequenceLabel = string | null | undefined;

/**
 * How far a presentation of the agent's work has come with its tool calls. The
 * conversation follows it, so a call shows up there when its work does.
 */
export type ToolCallProgress = {
  /** Calls the presentation has yet to reach. */
  waiting: ReadonlySet<string>;
  /** The call whose work it is showing right now. */
  working: string | null;
};

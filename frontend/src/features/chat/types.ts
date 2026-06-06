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

export type ToolCallItem = {
  id: string;
  text: string;
  status?: ToolCallStatus;
  actionType?: ToolCallActionType | string | null;
  detail?: string;
};

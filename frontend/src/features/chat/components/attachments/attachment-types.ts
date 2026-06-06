export type ChatAttachmentKind =
  | "spotify-track"
  | "spotify-playlist"
  | "spotify-artist";

export type ChatAttachment = {
  id: string;
  kind: ChatAttachmentKind;
  title: string;
  subtitle?: string;
  imageUrl?: string | null;
  spotifyId?: string;
};

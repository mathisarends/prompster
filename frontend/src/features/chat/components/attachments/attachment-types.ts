export type ChatAttachmentKind =
  | "image"
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
  file?: File;
  storageKey?: string;
  contentType?: string;
  sizeBytes?: number;
};

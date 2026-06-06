import type { ChatAttachmentKind } from "./attachment-types";

export type ParsedSpotifyRef = {
  kind: ChatAttachmentKind;
  id: string;
};

const KIND_BY_TYPE: Record<string, ChatAttachmentKind> = {
  track: "spotify-track",
  playlist: "spotify-playlist",
  artist: "spotify-artist",
};

const ID_PATTERN = /^[A-Za-z0-9]{22}$/;

export const parseSpotifyRef = (raw: string): ParsedSpotifyRef | null => {
  const trimmed = raw.trim();
  if (!trimmed) return null;

  const uriMatch = trimmed.match(/^spotify:(track|playlist|artist):([A-Za-z0-9]{22})$/);
  if (uriMatch) {
    return { kind: KIND_BY_TYPE[uriMatch[1]], id: uriMatch[2] };
  }

  const urlMatch = trimmed.match(
    /^(?:https?:\/\/)?open\.spotify\.com\/(?:intl-[a-z]+\/)?(track|playlist|artist)\/([A-Za-z0-9]{22})(?:[/?].*)?$/i,
  );
  if (urlMatch) {
    return { kind: KIND_BY_TYPE[urlMatch[1].toLowerCase()], id: urlMatch[2] };
  }

  return null;
};

export const isLikelySpotifyId = (raw: string) => ID_PATTERN.test(raw.trim());

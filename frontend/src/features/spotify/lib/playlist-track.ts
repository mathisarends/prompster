import type { PlaylistTrackResponse } from "@/api/generated/model";

export type PlaylistTrack = Omit<PlaylistTrackResponse, "year" | "coverUrl"> & {
  year: string;
  durationSeconds: number;
  coverUrl: string;
};

import { spotifyGetAccessToken } from "@/api/generated/spotify/spotify";

export const fetchSpotifyAccessToken = async (): Promise<string> => {
  const response = await spotifyGetAccessToken();
  return response.accessToken;
};

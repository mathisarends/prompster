import { useCallback, useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { getSpotifyConnectQueryKey } from "@/api/generated/spotify/spotify";
import { getGetMeQueryKey } from "@/api/generated/user-api";
import { AXIOS_INSTANCE } from "@/shared/api/http-client";

const SPOTIFY_OAUTH_MESSAGE_TYPE = "prompster-spotify-oauth";

type SpotifyOAuthPopupMessage = {
  type: typeof SPOTIFY_OAUTH_MESSAGE_TYPE;
  status: "success" | "error";
  reason?: string;
};

const isSpotifyOAuthPopupMessage = (
  data: unknown,
): data is SpotifyOAuthPopupMessage => {
  if (typeof data !== "object" || data === null) {
    return false;
  }

  const candidate = data as { type?: unknown; status?: unknown };
  return (
    candidate.type === SPOTIFY_OAUTH_MESSAGE_TYPE &&
    (candidate.status === "success" || candidate.status === "error")
  );
};

const resolveBackendOrigin = (): string => {
  const baseUrl =
    AXIOS_INSTANCE.defaults.baseURL ??
    `${window.location.protocol}//${window.location.hostname}:8000`;

  return new URL(baseUrl, window.location.origin).origin;
};

const getSpotifyConnectUrl = (): string => {
  const [spotifyConnectPath] = getSpotifyConnectQueryKey();
  return new URL(spotifyConnectPath, resolveBackendOrigin()).toString();
};

export const useSpotifyOAuthPopup = () => {
  const queryClient = useQueryClient();
  const [isSpotifyOAuthLoading, setIsSpotifyOAuthLoading] = useState(false);
  const spotifyOAuthPopupRef = useRef<Window | null>(null);
  const spotifyPopupClosedCheckRef = useRef<number | null>(null);

  const stopSpotifyPopupClosedCheck = useCallback(() => {
    if (spotifyPopupClosedCheckRef.current !== null) {
      window.clearInterval(spotifyPopupClosedCheckRef.current);
      spotifyPopupClosedCheckRef.current = null;
    }
  }, []);

  useEffect(() => {
    const backendOrigin = resolveBackendOrigin();

    const handleMessage = (event: MessageEvent) => {
      if (event.origin !== backendOrigin) return;
      if (!isSpotifyOAuthPopupMessage(event.data)) return;

      stopSpotifyPopupClosedCheck();
      spotifyOAuthPopupRef.current?.close();
      spotifyOAuthPopupRef.current = null;
      setIsSpotifyOAuthLoading(false);

      if (event.data.status === "success") {
        void queryClient.invalidateQueries({ queryKey: getGetMeQueryKey() });
        toast.success("Spotify verbunden.");
        return;
      }

      toast.error(
        event.data.reason === "access_denied"
          ? "Spotify-Verbindung abgebrochen."
          : "Spotify-Verbindung fehlgeschlagen.",
      );
    };

    window.addEventListener("message", handleMessage);
    return () => {
      window.removeEventListener("message", handleMessage);
      stopSpotifyPopupClosedCheck();
    };
  }, [queryClient, stopSpotifyPopupClosedCheck]);

  const openSpotifyOAuthPopup = useCallback(() => {
    if (isSpotifyOAuthLoading) return;

    const spotifyConnectUrl = getSpotifyConnectUrl();
    const oauthPopup = window.open(
      spotifyConnectUrl,
      SPOTIFY_OAUTH_MESSAGE_TYPE,
      "popup,width=520,height=720",
    );

    if (!oauthPopup) {
      window.location.assign(spotifyConnectUrl);
      return;
    }

    spotifyOAuthPopupRef.current = oauthPopup;
    setIsSpotifyOAuthLoading(true);

    stopSpotifyPopupClosedCheck();
    spotifyPopupClosedCheckRef.current = window.setInterval(() => {
      if (spotifyOAuthPopupRef.current?.closed) {
        stopSpotifyPopupClosedCheck();
        spotifyOAuthPopupRef.current = null;
        setIsSpotifyOAuthLoading(false);
      }
    }, 500);
  }, [isSpotifyOAuthLoading, stopSpotifyPopupClosedCheck]);

  return {
    isSpotifyOAuthLoading,
    openSpotifyOAuthPopup,
  };
};

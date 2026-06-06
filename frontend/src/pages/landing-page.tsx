import { useEffect, useRef, useState } from "react";

import { Badge } from "@/shared/ui/badge";
import { Button } from "@/shared/ui/button";
import { AXIOS_INSTANCE } from "@/shared/api/http-client";
import { useAuth } from "@/features/auth";
import { Sparkles } from "lucide-react";

const OAUTH_GOOGLE_MESSAGE_TYPE = "prompster-google-oauth";
const OAUTH_SPOTIFY_LOGIN_MESSAGE_TYPE = "prompster-spotify-login";

type GoogleOAuthPopupMessage = {
  type: typeof OAUTH_GOOGLE_MESSAGE_TYPE;
  status: "success" | "error";
  reason?: string;
};

type SpotifyLoginOAuthPopupMessage = {
  type: typeof OAUTH_SPOTIFY_LOGIN_MESSAGE_TYPE;
  status: "success" | "error";
  reason?: string;
};

type OAuthPopupMessage = GoogleOAuthPopupMessage | SpotifyLoginOAuthPopupMessage;

const isOAuthPopupMessage = (data: unknown): data is OAuthPopupMessage => {
  if (typeof data !== "object" || data === null) return false;
  const candidate = data as { type?: unknown; status?: unknown };
  return (
    (candidate.type === OAUTH_GOOGLE_MESSAGE_TYPE ||
      candidate.type === OAUTH_SPOTIFY_LOGIN_MESSAGE_TYPE) &&
    (candidate.status === "success" || candidate.status === "error")
  );
};

const resolveBackendOrigin = (): string => {
  const baseUrl =
    AXIOS_INSTANCE.defaults.baseURL ??
    `${window.location.protocol}//${window.location.hostname}:8000`;
  return new URL(baseUrl, window.location.origin).origin;
};

const SpotifyIcon = () => (
  <svg
    role="img"
    viewBox="0 0 24 24"
    className="size-5"
    fill="currentColor"
    xmlns="http://www.w3.org/2000/svg"
  >
    <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z" />
  </svg>
);

export const LandingPage = () => {
  const { signIn } = useAuth();
  const [isGoogleOAuthLoading, setIsGoogleOAuthLoading] = useState(false);
  const [isSpotifyOAuthLoading, setIsSpotifyOAuthLoading] = useState(false);
  const [oauthError, setOAuthError] = useState<string | null>(null);
  const oauthPopupRef = useRef<Window | null>(null);
  const popupClosedCheckRef = useRef<number | null>(null);

  const stopPopupClosedCheck = () => {
    if (popupClosedCheckRef.current !== null) {
      window.clearInterval(popupClosedCheckRef.current);
      popupClosedCheckRef.current = null;
    }
  };

  const startPopupClosedCheck = (
    setLoading: (v: boolean) => void,
  ) => {
    stopPopupClosedCheck();
    popupClosedCheckRef.current = window.setInterval(() => {
      if (oauthPopupRef.current?.closed) {
        stopPopupClosedCheck();
        oauthPopupRef.current = null;
        setLoading(false);
      }
    }, 500);
  };

  useEffect(() => {
    const backendOrigin = resolveBackendOrigin();

    const handleMessage = (event: MessageEvent) => {
      if (event.origin !== backendOrigin) return;
      if (!isOAuthPopupMessage(event.data)) return;

      stopPopupClosedCheck();
      oauthPopupRef.current?.close();
      oauthPopupRef.current = null;

      if (event.data.type === OAUTH_GOOGLE_MESSAGE_TYPE) {
        setIsGoogleOAuthLoading(false);
      } else {
        setIsSpotifyOAuthLoading(false);
      }

      if (event.data.status === "success") {
        setOAuthError(null);
        void signIn().catch(() => {
          setOAuthError(
            "Anmeldung abgeschlossen, aber die Sitzung konnte nicht geladen werden.",
          );
        });
      } else {
        if (event.data.type === OAUTH_GOOGLE_MESSAGE_TYPE) {
          setOAuthError(
            event.data.reason === "access_denied"
              ? "Google-Anmeldung abgebrochen."
              : "Google-Anmeldung fehlgeschlagen. Bitte erneut versuchen.",
          );
        } else {
          setOAuthError(
            event.data.reason === "access_denied"
              ? "Spotify-Anmeldung abgebrochen."
              : event.data.reason === "email_taken"
                ? "Diese E-Mail ist bereits mit einem anderen Konto verknuepft."
                : "Spotify-Anmeldung fehlgeschlagen. Bitte erneut versuchen.",
          );
        }
      }
    };

    window.addEventListener("message", handleMessage);
    return () => {
      window.removeEventListener("message", handleMessage);
      stopPopupClosedCheck();
    };
  }, [signIn]);

  const openOAuthPopup = (
    url: string,
    windowName: string,
    setLoading: (v: boolean) => void,
  ) => {
    const popup = window.open(url, windowName, "popup,width=520,height=720");

    if (!popup) {
      window.location.assign(url);
      return;
    }

    oauthPopupRef.current = popup;
    setOAuthError(null);
    setLoading(true);
    startPopupClosedCheck(setLoading);
  };

  const handleGoogleSignIn = () => {
    if (isGoogleOAuthLoading || isSpotifyOAuthLoading) return;

    const googleLoginUrl = new URL(
      "/api/v1/auth/google/login",
      resolveBackendOrigin(),
    ).toString();

    openOAuthPopup(
      googleLoginUrl,
      OAUTH_GOOGLE_MESSAGE_TYPE,
      setIsGoogleOAuthLoading,
    );
  };

  const handleSpotifySignIn = () => {
    if (isGoogleOAuthLoading || isSpotifyOAuthLoading) return;

    const spotifyLoginUrl = new URL(
      "/api/v1/auth/spotify/login",
      resolveBackendOrigin(),
    ).toString();

    openOAuthPopup(
      spotifyLoginUrl,
      OAUTH_SPOTIFY_LOGIN_MESSAGE_TYPE,
      setIsSpotifyOAuthLoading,
    );
  };

  const isAnyLoading = isGoogleOAuthLoading || isSpotifyOAuthLoading;

  return (
    <div className="home-page-background min-h-dvh text-foreground">
      <main className="relative z-10 flex min-h-dvh flex-col justify-center px-4 py-10 sm:px-8 sm:py-14">
        <div className="mx-auto w-full max-w-md -translate-y-6 sm:-translate-y-8">
          <section className="space-y-8">
            <div className="space-y-4 text-center sm:space-y-5">
              <Badge
                variant="secondary"
                className="mx-auto w-fit gap-1 px-2.5 py-1"
              >
                <Sparkles className="size-3.5" />
                Prompster
              </Badge>
              <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">
                Willkommen zurueck
              </h1>
              <p className="mx-auto max-w-sm text-sm text-muted-foreground sm:text-base">
                Melde dich an, um deine Karten-Decks zu erstellen.
              </p>
            </div>

            <div className="space-y-3 rounded-2xl bg-card/55 p-5 backdrop-blur-md sm:p-6">
              <Button
                type="button"
                variant="outline"
                onClick={handleGoogleSignIn}
                disabled={isAnyLoading}
                className="h-10 w-full"
              >
                <span className="grid size-5 place-items-center rounded-full bg-white text-xs font-bold text-[#4285f4]">
                  G
                </span>
                {isGoogleOAuthLoading
                  ? "Google-Anmeldung laeuft..."
                  : "Mit Google fortfahren"}
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={handleSpotifySignIn}
                disabled={isAnyLoading}
                className="h-10 w-full"
              >
                <SpotifyIcon />
                {isSpotifyOAuthLoading
                  ? "Spotify-Anmeldung laeuft..."
                  : "Mit Spotify fortfahren"}
              </Button>
              {oauthError ? (
                <p className="text-center text-sm text-destructive">
                  {oauthError}
                </p>
              ) : null}
            </div>
          </section>
        </div>
      </main>
    </div>
  );
};

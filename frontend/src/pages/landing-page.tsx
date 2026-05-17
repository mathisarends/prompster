import { useEffect, useRef, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { AXIOS_INSTANCE } from "@/api/http-client";
import { useAuth } from "@/auth/use-auth";
import { Sparkles } from "lucide-react";

const OAUTH_MESSAGE_TYPE = "prompster-google-oauth";

type OAuthPopupMessage = {
  type: typeof OAUTH_MESSAGE_TYPE;
  status: "success" | "error";
  reason?: string;
};

const isOAuthPopupMessage = (data: unknown): data is OAuthPopupMessage => {
  if (typeof data !== "object" || data === null) return false;
  const candidate = data as { type?: unknown; status?: unknown };
  return (
    candidate.type === OAUTH_MESSAGE_TYPE &&
    (candidate.status === "success" || candidate.status === "error")
  );
};

const resolveBackendOrigin = (): string => {
  const baseUrl =
    AXIOS_INSTANCE.defaults.baseURL ??
    `${window.location.protocol}//${window.location.hostname}:8000`;
  return new URL(baseUrl, window.location.origin).origin;
};

export const LandingPage = () => {
  const { signIn } = useAuth();
  const [isGoogleOAuthLoading, setIsGoogleOAuthLoading] = useState(false);
  const [oauthError, setOAuthError] = useState<string | null>(null);
  const oauthPopupRef = useRef<Window | null>(null);
  const popupClosedCheckRef = useRef<number | null>(null);

  const stopPopupClosedCheck = () => {
    if (popupClosedCheckRef.current !== null) {
      window.clearInterval(popupClosedCheckRef.current);
      popupClosedCheckRef.current = null;
    }
  };

  useEffect(() => {
    const backendOrigin = resolveBackendOrigin();

    const handleMessage = (event: MessageEvent) => {
      if (event.origin !== backendOrigin) return;
      if (!isOAuthPopupMessage(event.data)) return;

      stopPopupClosedCheck();
      oauthPopupRef.current?.close();
      oauthPopupRef.current = null;
      setIsGoogleOAuthLoading(false);

      if (event.data.status === "success") {
        setOAuthError(null);
        void signIn();
      } else {
        setOAuthError(
          event.data.reason === "access_denied"
            ? "Google-Anmeldung abgebrochen."
            : "Google-Anmeldung fehlgeschlagen. Bitte erneut versuchen.",
        );
      }
    };

    window.addEventListener("message", handleMessage);
    return () => {
      window.removeEventListener("message", handleMessage);
      stopPopupClosedCheck();
    };
  }, [signIn]);

  const handleGoogleSignIn = () => {
    if (isGoogleOAuthLoading) return;

    const googleLoginUrl = new URL(
      "/api/v1/auth/google/login",
      resolveBackendOrigin(),
    ).toString();
    const oauthPopup = window.open(
      googleLoginUrl,
      "prompster-google-oauth",
      "popup,width=520,height=720",
    );

    if (!oauthPopup) {
      window.location.assign(googleLoginUrl);
      return;
    }

    oauthPopupRef.current = oauthPopup;
    setOAuthError(null);
    setIsGoogleOAuthLoading(true);

    stopPopupClosedCheck();
    popupClosedCheckRef.current = window.setInterval(() => {
      if (oauthPopupRef.current?.closed) {
        stopPopupClosedCheck();
        oauthPopupRef.current = null;
        setIsGoogleOAuthLoading(false);
      }
    }, 500);
  };

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

            <div className="space-y-4 rounded-2xl bg-card/55 p-5 backdrop-blur-md sm:p-6">
              <Button
                type="button"
                variant="outline"
                onClick={handleGoogleSignIn}
                disabled={isGoogleOAuthLoading}
                className="h-10 w-full"
              >
                <span className="grid size-5 place-items-center rounded-full bg-white text-xs font-bold text-[#4285f4]">
                  G
                </span>
                {isGoogleOAuthLoading
                  ? "Google-Anmeldung laeuft..."
                  : "Mit Google fortfahren"}
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

import { useEffect, useRef, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { fetchCurrentUser, getGoogleOAuthLoginUrl } from "@/api/auth";
import { Sparkles } from "lucide-react";

type LandingPageProps = {
  onSignIn: () => void;
};

export const LandingPage = ({ onSignIn }: LandingPageProps) => {
  const [email, setEmail] = useState("");
  const [isGoogleOAuthLoading, setIsGoogleOAuthLoading] = useState(false);
  const oauthPopupRef = useRef<Window | null>(null);
  const oauthPollTimeoutRef = useRef<number | null>(null);
  const oauthPollAttemptRef = useRef(0);

  const submitEmail = () => {
    if (!email.trim()) return;
    onSignIn();
  };

  const clearOAuthPolling = () => {
    if (oauthPollTimeoutRef.current !== null) {
      window.clearTimeout(oauthPollTimeoutRef.current);
      oauthPollTimeoutRef.current = null;
    }
  };

  const stopOAuthFlow = () => {
    clearOAuthPolling();
    oauthPopupRef.current = null;
    oauthPollAttemptRef.current = 0;
    setIsGoogleOAuthLoading(false);
  };

  const pollOAuthCompletion = () => {
    const oauthPopup = oauthPopupRef.current;
    if (!oauthPopup || oauthPopup.closed) {
      stopOAuthFlow();
      return;
    }

    if (oauthPollAttemptRef.current >= 180) {
      oauthPopup.close();
      stopOAuthFlow();
      return;
    }

    void fetchCurrentUser()
      .then(() => {
        oauthPopup.close();
        stopOAuthFlow();
        onSignIn();
      })
      .catch(() => {
        oauthPollAttemptRef.current += 1;
        oauthPollTimeoutRef.current = window.setTimeout(
          pollOAuthCompletion,
          1000,
        );
      });
  };

  const handleGoogleSignIn = () => {
    if (isGoogleOAuthLoading) {
      return;
    }

    const googleLoginUrl = getGoogleOAuthLoginUrl();
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
    setIsGoogleOAuthLoading(true);
    clearOAuthPolling();
    pollOAuthCompletion();
  };

  useEffect(() => {
    return () => {
      clearOAuthPolling();
    };
  }, []);

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
                Willkommen zurück
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

              <div className="flex items-center gap-3 text-[10px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                <span className="h-px flex-1 bg-border" />
                oder
                <span className="h-px flex-1 bg-border" />
              </div>

              <form
                className="space-y-3"
                onSubmit={(event) => {
                  event.preventDefault();
                  submitEmail();
                }}
              >
                <Input
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="E-Mail"
                  className="h-10"
                />
                <Input
                  type="password"
                  placeholder="Passwort"
                  className="h-10"
                />
                <Button
                  type="submit"
                  disabled={!email.trim()}
                  className="h-10 w-full"
                >
                  Anmelden
                </Button>
              </form>
            </div>

            <p className="text-center text-xs text-muted-foreground">
              Noch kein Konto?{" "}
              <button
                type="button"
                onClick={onSignIn}
                className="font-medium text-foreground underline-offset-4 hover:underline"
              >
                Registrieren
              </button>
            </p>
          </section>
        </div>
      </main>
    </div>
  );
};

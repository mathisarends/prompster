import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Sparkles } from "lucide-react";

type LandingPageProps = {
  onSignIn: () => void;
};

export const LandingPage = ({ onSignIn }: LandingPageProps) => {
  const [email, setEmail] = useState("");

  const submitEmail = () => {
    if (!email.trim()) return;
    onSignIn();
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
                onClick={onSignIn}
                className="h-10 w-full"
              >
                <span className="grid size-5 place-items-center rounded-full bg-white text-xs font-bold text-[#4285f4]">
                  G
                </span>
                Mit Google fortfahren
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

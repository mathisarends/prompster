import { useState } from "react";
import { Check, ChevronDown, Mail, MonitorDown, Music2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type LandingPageProps = {
  onSignIn: () => void;
};

const deckProgressSteps = [
  { label: "Mit Google anmelden", status: "done" },
  { label: "Spotify verbinden", status: "active" },
  { label: "Hitster-Deck beschreiben", status: "next" },
  { label: "Playlist und Karten bauen", status: "next" },
] as const;

export const LandingPage = ({ onSignIn }: LandingPageProps) => {
  const [email, setEmail] = useState("");

  const submitEmailMock = () => {
    if (!email.trim()) return;

    onSignIn();
  };

  return (
    <main className="min-h-dvh overflow-hidden bg-[#11110f] text-white">
      <div className="mx-auto flex min-h-dvh w-full max-w-7xl flex-col px-5 py-5 sm:px-8 lg:px-12">
        <header className="flex h-12 items-center">
          <div className="flex items-center gap-2.5">
            <div className="grid size-7 place-items-center rounded-md bg-[#1db954] text-sm font-bold text-[#07120b]">
              P
            </div>
            <span className="text-xl font-semibold tracking-tight">
              Prompster
            </span>
          </div>
        </header>

        <section className="grid flex-1 items-center gap-10 py-8 lg:grid-cols-[0.88fr_1.12fr] lg:gap-14 lg:py-12">
          <div className="mx-auto w-full max-w-md lg:mx-0 lg:justify-self-center">
            <div className="mb-7 space-y-4 sm:mb-8">
              <h1 className="text-balance text-5xl font-semibold leading-[0.98] tracking-normal sm:text-6xl lg:text-7xl">
                Denk schnell,
                <br />
                bau schneller
              </h1>
              <p className="max-w-sm text-base font-medium text-white/84">
                Im Chat brainstormen, mit Spotify verbinden, Hitster-Decks
                erstellen.
              </p>
            </div>

            <div className="rounded-3xl border border-white/10 bg-white/[0.02] p-5 shadow-2xl shadow-black/30 backdrop-blur">
              <Button
                type="button"
                variant="outline"
                onClick={onSignIn}
                className="h-10 w-full border-white/14 bg-transparent text-white hover:bg-white/8 hover:text-white"
              >
                <span className="grid size-5 place-items-center rounded-full bg-white text-sm font-bold text-[#4285f4]">
                  G
                </span>
                Mit Google fortfahren
              </Button>

              <div className="my-3 flex items-center gap-3 text-[10px] font-semibold uppercase tracking-[0.12em] text-white/58">
                <span className="h-px flex-1 bg-white/10" />
                oder
                <span className="h-px flex-1 bg-white/10" />
              </div>

              <div className="space-y-3">
                <Input
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") submitEmailMock();
                  }}
                  placeholder="Gib deine E-Mail ein"
                  className="h-10 border-white/10 bg-white/12 text-white placeholder:text-white/54 focus-visible:ring-white/18"
                />
                <Button
                  type="button"
                  variant="secondary"
                  onClick={submitEmailMock}
                  disabled={!email.trim()}
                  className="h-10 w-full bg-white text-[#171713] hover:bg-white/88"
                >
                  <Mail className="size-4" />
                  Mit E-Mail fortfahren
                </Button>
              </div>

              <p className="mt-3 text-center text-xs leading-5 text-white/46">
                Indem du fortfährst, startest du deine Prompster-Session.
              </p>
            </div>

            <Button
              type="button"
              variant="outline"
              className="mx-auto mt-5 flex h-9 border-white/14 bg-transparent px-4 text-white/92 hover:bg-white/8 hover:text-white"
            >
              <MonitorDown className="size-4" />
              Desktop-App herunterladen
            </Button>
          </div>

          <div className="relative mx-auto w-full max-w-xl lg:max-w-2xl">
            <div className="aspect-[0.92] min-h-[28rem] rounded-2xl bg-[#f7f4ee] p-6 shadow-[0_28px_90px_rgb(0_0_0_/0.42)] sm:p-10 lg:min-h-[40rem]">
              <div className="flex h-full items-center justify-center">
                <div className="w-full max-w-lg rounded-3xl border border-black/12 bg-white p-6 text-[#25231f] shadow-sm sm:p-8">
                  <div className="mb-7 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="grid size-9 place-items-center rounded-full bg-[#1db954]/12 text-[#13853d]">
                        <Music2 className="size-5" />
                      </div>
                      <h2 className="text-xl font-semibold tracking-normal">
                        Fortschritt
                      </h2>
                    </div>
                    <ChevronDown className="size-5 text-black/58" />
                  </div>

                  <ol className="space-y-6">
                    {deckProgressSteps.map((step, index) => (
                      <li key={step.label} className="flex items-center gap-4">
                        <div
                          className={
                            step.status === "done"
                              ? "grid size-9 shrink-0 place-items-center rounded-full bg-[#2f8de4] text-white"
                              : step.status === "active"
                                ? "grid size-9 shrink-0 place-items-center rounded-full border-2 border-[#2f8de4] bg-white text-[#2f5f96]"
                                : "grid size-9 shrink-0 place-items-center rounded-full border border-black/14 bg-white text-black/58"
                          }
                        >
                          {step.status === "done" ? (
                            <Check className="size-5" />
                          ) : (
                            <span className="text-xl font-medium">
                              {index + 1}
                            </span>
                          )}
                        </div>
                        <span
                          className={
                            step.status === "done"
                              ? "text-xl text-black/48 line-through decoration-black/36 decoration-2"
                              : step.status === "active"
                                ? "text-xl font-medium text-[#22201d]"
                                : "text-xl text-black/48"
                          }
                        >
                          {step.label}
                        </span>
                      </li>
                    ))}
                  </ol>
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
};

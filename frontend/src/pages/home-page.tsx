import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { Mic2, PartyPopper, Sparkles, Trophy } from "lucide-react";

import {
  createSession,
  getListSessionsQueryKey,
} from "@/api/generated/session-api";
import { ChatInputBox } from "@/features/chat";
import { Chip } from "@/shared/ui/chip";
import { Badge } from "@/shared/ui/badge";

const PROMPT_SUGGESTIONS = [
  {
    label: "Hip-Hop der 90er",
    icon: Mic2,
    prompt:
      "Erstell mir ein Deck zu Hip-Hop-Klassikern der 90er - bekannte Songs, die jeder mitsingen kann.",
  },
  {
    label: "Eurovision Hits",
    icon: Trophy,
    prompt:
      "Ich moechte ein Deck mit den groessten Eurovision-Hits von 2000 bis 2020.",
  },
  {
    label: "Party-Anthems",
    icon: PartyPopper,
    prompt:
      "Bau mir ein Deck mit Party-Anthems aus Rock und Pop, das auf jeder Feier funktioniert.",
  },
] as const;

export const HomePage = () => {
  const [prompt, setPrompt] = useState("");
  const [isCreatingSession, setIsCreatingSession] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const startChat = async (text: string) => {
    if (isCreatingSession) return;

    setIsCreatingSession(true);
    setErrorMessage(null);

    try {
      const session = await createSession({ initialPrompt: text });
      await queryClient.invalidateQueries({
        queryKey: getListSessionsQueryKey(),
      });
      navigate(`/chat/${session.id}`, {
        state: { session, streamInitialResponse: true, initialPrompt: text },
      });
    } catch {
      setErrorMessage("Session konnte nicht gestartet werden.");
      setIsCreatingSession(false);
    }
  };

  return (
    <div className="home-page-background min-h-dvh text-foreground">
      <main className="relative z-10 flex min-h-dvh flex-col justify-center px-4 py-10 sm:px-8 sm:py-14">
        <div className="mx-auto w-full max-w-4xl -translate-y-6 sm:-translate-y-8">
          <section className="space-y-8">
            <div className="space-y-4 text-center sm:space-y-5">
              <Badge
                variant="secondary"
                className="mx-auto w-fit gap-1 px-2.5 py-1"
              >
                <Sparkles className="size-3.5" />
                Neues Karten-Deck
              </Badge>
              <h1 className="mx-auto max-w-3xl text-4xl font-semibold tracking-tight sm:text-6xl">
                Welche Musik soll dein Deck haben?
              </h1>
            </div>

            <div className="space-y-4">
              <ChatInputBox
                value={prompt}
                onChange={setPrompt}
                onSubmit={startChat}
                placeholder='z.B. "Hip-Hop Klassiker der 90er" oder "Eurovision Hits 2000-2020"'
                sendButtonAriaLabel="Chat starten"
                disabled={isCreatingSession}
                isSubmitting={isCreatingSession}
                clearOnSubmit={false}
              />

              <div className="flex flex-wrap justify-center gap-2.5">
                {PROMPT_SUGGESTIONS.map((suggestion) => (
                  <Chip
                    key={suggestion.label}
                    onClick={() => setPrompt(suggestion.prompt)}
                    disabled={isCreatingSession}
                    icon={suggestion.icon}
                    label={suggestion.label}
                  />
                ))}
              </div>
            </div>
            {errorMessage && (
              <p className="text-center text-sm text-destructive">
                {errorMessage}
              </p>
            )}
          </section>
        </div>
      </main>
    </div>
  );
};

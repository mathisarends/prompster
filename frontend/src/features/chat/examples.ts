import { msg } from "@lit/localize";
import type { SongCard } from "@features/deck/components/music-card";

/** Static examples for the landing-page illustration, never generated from a prompt. */
export const exampleCards: SongCard[] = [
  { id: "example-1976", title: "Dancing Queen", artist: "ABBA", year: 1976 },
  { id: "example-1991", title: "Smells Like Teen Spirit", artist: "Nirvana", year: 1991 },
  { id: "example-2000", title: "One More Time", artist: "Daft Punk", year: 2000 },
];
export const starters = () =>
  [
    {
      icon: "disc",
      title: msg("Zurück in die 90er"),
      description: msg("Boybands, Britpop & große Gefühle"),
      prompt: msg(
        "Ein Deck mit den großen Hits der 90er: von Boybands bis Britpop, für einen nostalgischen Spieleabend.",
      ),
    },
    {
      icon: "headphones",
      title: msg("Einmal quer durch die Zeit"),
      description: msg("Von Disco bis zu deinen Lieblingshits"),
      prompt: msg(
        "Ein bunt gemischtes Musikdeck von den 70ern bis heute. Bekannte Songs und ein paar überraschende Entdeckungen.",
      ),
    },
    {
      icon: "sparkles",
      title: msg("Die Mitsing-Edition"),
      description: msg("Songs, bei denen niemand still bleibt"),
      prompt: msg(
        "Ein Musikdeck voller Partyklassiker und Mitsing-Hits für einen Spieleabend mit Freunden.",
      ),
    },
  ] as const;

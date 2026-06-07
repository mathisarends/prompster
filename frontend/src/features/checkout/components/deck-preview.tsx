import { Copy } from "lucide-react";

import type { CheckoutDeck } from "../types";
import { QrCard } from "./qr-card";

type DeckPreviewProps = {
  deck: CheckoutDeck;
};

export const DeckPreview = ({ deck }: DeckPreviewProps) => (
  <section className="space-y-4">
    <div className="flex items-center gap-2 text-sm font-bold uppercase tracking-[0.12em] text-emerald-300">
      <Copy className="size-4" />
      Dein Deck - Vorschau
    </div>

    <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
      <h2 className="text-2xl font-bold tracking-tight text-white sm:text-3xl">
        {deck.title}
      </h2>
      <div className="flex flex-wrap items-center gap-3 text-sm font-semibold text-white/48 sm:text-base">
        <span className="text-white">{deck.cardCount}</span>
        <span>Karten</span>
        {deck.meta.map((item) => (
          <span key={item} className="flex items-center gap-3">
            <span className="size-1 rounded-full bg-white/34" aria-hidden />
            <span className={item.includes("-") ? "text-white" : undefined}>
              {item}
            </span>
          </span>
        ))}
      </div>
    </div>

    <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-5">
      {deck.previewCards.map((card) => (
        <QrCard
          key={card.id}
          artist={card.artist}
          seed={card.seed}
          title={card.title}
          year={card.year}
        />
      ))}
    </div>

    <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-5" aria-hidden>
      {deck.previewCards.map((card) => (
        <QrCard
          key={`${card.id}-locked`}
          artist={card.artist}
          seed={card.seed + 4}
          title={card.title}
          year={card.year}
          lockedLabel={deck.lockedCardsLabel}
        />
      ))}
    </div>
  </section>
);

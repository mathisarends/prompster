import { Check, Download, Music2, Sparkles } from "lucide-react";

import type { CheckoutDeck, CheckoutPackage } from "../types";

type SuccessStepProps = {
  deck: CheckoutDeck;
  selectedPackage: CheckoutPackage;
  onRestart: () => void;
};

export const SuccessStep = ({
  deck,
  selectedPackage,
  onRestart,
}: SuccessStepProps) => (
  <section className="mx-auto flex max-w-3xl flex-col items-center py-10 text-center">
    <div className="grid size-28 place-items-center rounded-full border border-emerald-400 bg-emerald-400/10 shadow-[0_0_0_14px_hsl(154_70%_40%/0.09),0_30px_90px_hsl(154_70%_36%/0.28)]">
      <Check className="size-12 text-emerald-300" />
    </div>

    <h1 className="mt-9 text-5xl font-black tracking-[-0.06em] text-white">
      Zahlung erfolgreich!
    </h1>
    <p className="mt-4 max-w-2xl text-xl font-medium leading-8 text-white/55">
      Danke fuer deinen Kauf. Dein Deck &lt;{deck.title}&gt; ist startklar -
      viel Spass beim Spielen!
    </p>

    <div className="mt-10 w-full rounded-3xl border border-white/10 bg-[#121718] p-6 text-left">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-sm font-black text-white/48">
            Bestellbestaetigung
          </p>
          <p className="mt-1 text-sm font-semibold text-white/45">PR-9705-HX</p>
        </div>
        <div className="text-right">
          <p className="text-sm font-bold text-white/45">
            {selectedPackage.name}-Deck
          </p>
          <p className="text-xl font-black text-white">
            {deck.cardCount} Karten
          </p>
        </div>
      </div>

      <div className="mt-6 flex flex-col gap-4 rounded-2xl border border-white/12 bg-black/24 p-5 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-4">
          <div className="grid size-14 place-items-center rounded-xl bg-emerald-400/12 text-emerald-300">
            <Download className="size-7" />
          </div>
          <div>
            <p className="text-lg font-black text-white">{deck.title}.pdf</p>
            <p className="mt-1 text-sm font-semibold text-white/50">
              Druckfertig - A4 - {deck.cardCount} Karten - ~2,4 MB
            </p>
          </div>
        </div>
        <button
          type="button"
          className="rounded-xl bg-emerald-400 px-7 py-4 text-base font-black text-[#06110d] transition hover:bg-emerald-300"
        >
          PDF herunterladen
        </button>
      </div>

      <ol className="mt-7 space-y-5">
        {[
          [
            "Check deine Mails.",
            "Wir haben Download-Link & Rechnung an deine Adresse geschickt.",
          ],
          [
            "Drucken & ausschneiden.",
            "Doppelseitig auf festem Papier, an den Hilfslinien schneiden.",
          ],
          [
            "Playlist verbinden.",
            "Scanne eine Karte und Spotify spielt den Song sofort ab.",
          ],
        ].map(([title, text], index) => (
          <li key={title} className="flex gap-4 text-base font-medium">
            <span className="grid size-8 shrink-0 place-items-center rounded-full border border-white/12 bg-white/6 text-sm font-black text-white/56">
              {index + 1}
            </span>
            <p className="text-white/55">
              <strong className="text-white">{title}</strong> {text}
            </p>
          </li>
        ))}
      </ol>
    </div>

    <div className="mt-8 flex flex-col gap-4 sm:flex-row">
      <button
        type="button"
        onClick={onRestart}
        className="inline-flex items-center justify-center gap-3 rounded-xl border border-white/14 bg-white/6 px-7 py-4 text-base font-black text-white transition hover:bg-white/10"
      >
        <Music2 className="size-5" />
        Neues Deck erstellen
      </button>
      <button
        type="button"
        className="inline-flex items-center justify-center gap-3 rounded-xl border border-white/14 bg-white/6 px-7 py-4 text-base font-black text-white transition hover:bg-white/10"
      >
        <Sparkles className="size-5" />
        Spotify-Playlist oeffnen
      </button>
    </div>
  </section>
);

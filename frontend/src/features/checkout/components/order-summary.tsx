import { Music2, RefreshCw, ShieldCheck, Zap } from "lucide-react";

import type { CheckoutDeck, CheckoutPackage } from "../types";

type OrderSummaryProps = {
  deck: CheckoutDeck;
  selectedPackage: CheckoutPackage;
};

export const OrderSummary = ({ deck, selectedPackage }: OrderSummaryProps) => (
  <aside className="space-y-6">
    <div className="overflow-hidden rounded-3xl border border-white/10 bg-[#121718]">
      <div className="flex items-center gap-4 p-6">
        <div className="grid size-16 place-items-center rounded-2xl border border-fuchsia-500/35 bg-black/25 text-fuchsia-400">
          <Music2 className="size-7" />
        </div>
        <div>
          <h2 className="text-xl font-black tracking-tight text-white">
            {deck.title}
          </h2>
          <p className="mt-1 text-sm font-semibold text-white/48">
            {selectedPackage.name} - {deck.cardCount} Karten - digital
          </p>
        </div>
      </div>
      <div className="border-t border-white/10 p-6">
        <div className="flex items-center justify-between text-base font-medium text-white/52">
          <span>Deck &lt;{selectedPackage.name}&gt;</span>
          <span className="font-bold text-white">
            {selectedPackage.price} EUR
          </span>
        </div>
        <div className="my-6 h-px bg-white/10" />
        <div className="flex items-end justify-between gap-4">
          <span className="text-lg font-black text-white">Gesamt</span>
          <div className="text-right">
            <span className="text-4xl font-black tracking-[-0.06em] text-white">
              {selectedPackage.price} EUR
            </span>
            <span className="ml-2 text-sm font-bold text-white/34">
              inkl. MwSt.
            </span>
          </div>
        </div>
      </div>
    </div>

    <div className="space-y-4 text-base font-medium text-white/55">
      <p className="flex gap-3">
        <ShieldCheck className="mt-0.5 size-5 shrink-0 text-emerald-300" />
        <span>
          <strong className="text-white">SSL-verschluesselt.</strong> Zahlung
          sicher ueber Stripe & PayPal abgewickelt.
        </span>
      </p>
      <p className="flex gap-3">
        <RefreshCw className="mt-0.5 size-5 shrink-0 text-emerald-300" />
        <span>
          <strong className="text-white">14 Tage Geld-zurueck-Garantie</strong>{" "}
          bei digitalen Decks ohne Risiko.
        </span>
      </p>
      <p className="flex gap-3">
        <Zap className="mt-0.5 size-5 shrink-0 text-emerald-300" />
        <span>
          <strong className="text-white">Sofortiger Zugriff</strong> aufs PDF
          direkt nach dem Kauf.
        </span>
      </p>
    </div>
  </aside>
);

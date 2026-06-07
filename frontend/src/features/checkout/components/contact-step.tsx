import { ArrowLeft, ArrowRight, Mail, TicketPercent } from "lucide-react";

import type { CheckoutDeck, CheckoutPackage } from "../types";
import { OrderSummary } from "./order-summary";

type ContactStepProps = {
  deck: CheckoutDeck;
  selectedPackage: CheckoutPackage;
  onBack: () => void;
  onContinue: () => void;
};

export const ContactStep = ({
  deck,
  selectedPackage,
  onBack,
  onContinue,
}: ContactStepProps) => (
  <div className="grid gap-10 lg:grid-cols-[minmax(0,1fr)_30rem]">
    <section className="space-y-8">
      <div>
        <h1 className="text-4xl font-black tracking-[-0.05em] text-white">
          Deine Kontaktdaten
        </h1>
        <p className="mt-4 text-lg font-medium text-white/55">
          Wir schicken dir den Download-Link und die Rechnung an diese Adresse.
        </p>
      </div>

      <div className="rounded-3xl border border-white/10 bg-[#121718] p-8">
        <div className="flex gap-4">
          <span className="grid size-8 shrink-0 place-items-center rounded-full bg-white/8 text-sm font-black text-white/52">
            1
          </span>
          <div>
            <h2 className="text-xl font-black text-white">Kontakt</h2>
            <p className="mt-2 text-base font-medium text-white/50">
              Fuer Rechnung & Download-Link.
            </p>
          </div>
        </div>

        <label className="mt-8 block">
          <span className="text-sm font-bold text-white/48">
            E-Mail-Adresse
          </span>
          <span className="mt-3 flex h-14 items-center gap-3 rounded-xl border border-white/14 bg-black/35 px-4 text-white/48 focus-within:border-emerald-400">
            <Mail className="size-5" />
            <input
              className="w-full bg-transparent text-base font-medium outline-none placeholder:text-white/35"
              placeholder="max@beispiel.de"
              type="email"
            />
          </span>
        </label>
      </div>
    </section>

    <section className="space-y-5">
      <OrderSummary deck={deck} selectedPackage={selectedPackage} />

      <div className="flex gap-3">
        <label className="flex h-14 min-w-0 flex-1 items-center gap-2 rounded-xl border border-white/12 bg-black/20 px-4 text-white/32">
          <TicketPercent className="size-5" />
          <input
            className="min-w-0 flex-1 bg-transparent text-sm font-semibold outline-none placeholder:text-white/32"
            placeholder="Gutscheincode"
          />
        </label>
        <button
          type="button"
          className="rounded-xl border border-white/12 bg-white/8 px-5 font-black text-white transition hover:bg-white/12"
        >
          Einloesen
        </button>
      </div>

      <div className="flex gap-4">
        <button
          type="button"
          onClick={onBack}
          className="grid size-14 shrink-0 place-items-center rounded-xl border border-white/12 bg-white/6 text-white transition hover:bg-white/10"
          aria-label="Zurueck"
        >
          <ArrowLeft className="size-5" />
        </button>
        <button
          type="button"
          onClick={onContinue}
          className="group inline-flex h-14 flex-1 items-center justify-center gap-3 rounded-xl bg-emerald-400 px-8 text-lg font-black text-[#06110d] transition hover:bg-emerald-300"
        >
          Weiter zur Zahlung
          <ArrowRight className="size-5 transition group-hover:translate-x-1" />
        </button>
      </div>
    </section>
  </div>
);

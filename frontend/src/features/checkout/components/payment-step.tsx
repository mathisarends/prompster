import { ArrowLeft, CreditCard, LockKeyhole, User } from "lucide-react";

import { cn } from "@/shared/lib/utils";

import type { CheckoutDeck, CheckoutPackage } from "../types";
import { OrderSummary } from "./order-summary";

type PaymentStepProps = {
  deck: CheckoutDeck;
  selectedPackage: CheckoutPackage;
  onBack: () => void;
  onContinue: () => void;
};

const paymentMethods = [
  { id: "card", label: "Kreditkarte", detail: "VISA  MC", selected: true },
  { id: "paypal", label: "PayPal", detail: "PayPal", selected: false },
];

export const PaymentStep = ({
  deck,
  selectedPackage,
  onBack,
  onContinue,
}: PaymentStepProps) => (
  <div className="grid gap-10 lg:grid-cols-[minmax(0,1fr)_30rem]">
    <section className="space-y-8">
      <div>
        <h1 className="text-4xl font-black tracking-[-0.05em] text-white">
          Bezahlung
        </h1>
        <p className="mt-4 text-lg font-medium text-white/55">
          Waehle deine Zahlungsart. Alle Zahlungen laufen verschluesselt ueber
          Stripe.
        </p>
      </div>

      <div className="rounded-3xl border border-white/10 bg-[#121718] p-8">
        <div className="grid gap-4 sm:grid-cols-2">
          {paymentMethods.map((method) => (
            <button
              key={method.id}
              type="button"
              className={cn(
                "flex h-16 items-center justify-between rounded-xl border px-5 text-left transition",
                method.selected
                  ? "border-emerald-400 bg-emerald-400/8"
                  : "border-white/10 bg-black/28 hover:border-white/20",
              )}
            >
              <span className="flex items-center gap-3">
                <span
                  className={cn(
                    "grid size-6 place-items-center rounded-full border",
                    method.selected ? "border-emerald-400" : "border-white/18",
                  )}
                >
                  {method.selected ? (
                    <span className="size-2.5 rounded-full bg-emerald-400" />
                  ) : null}
                </span>
                <span className="text-lg font-black text-white">
                  {method.label}
                </span>
              </span>
              <span className="text-xs font-black text-white/70">
                {method.detail}
              </span>
            </button>
          ))}
        </div>

        <div className="mt-7 space-y-5">
          <label className="block">
            <span className="text-sm font-bold text-white/48">
              Karteninhaber
            </span>
            <span className="mt-3 flex h-14 items-center gap-3 rounded-xl border border-white/14 bg-black/35 px-4 text-white/48 focus-within:border-emerald-400">
              <User className="size-5" />
              <input
                className="w-full bg-transparent text-base font-medium outline-none placeholder:text-white/35"
                placeholder="Max Mustermann"
              />
            </span>
          </label>

          <label className="block">
            <span className="text-sm font-bold text-white/48">
              Kartennummer
            </span>
            <span className="mt-3 flex h-14 items-center gap-3 rounded-xl border border-white/14 bg-black/35 px-4 text-white/48 focus-within:border-emerald-400">
              <CreditCard className="size-5" />
              <input
                className="w-full bg-transparent text-base font-medium outline-none placeholder:text-white/35"
                placeholder="1234 5678 9012 3456"
              />
            </span>
          </label>

          <div className="grid gap-5 sm:grid-cols-2">
            <label className="block">
              <span className="text-sm font-bold text-white/48">
                Gueltig bis
              </span>
              <span className="mt-3 flex h-14 items-center rounded-xl border border-white/14 bg-black/35 px-4 focus-within:border-emerald-400">
                <input
                  className="w-full bg-transparent text-base font-medium outline-none placeholder:text-white/35"
                  placeholder="MM / JJ"
                />
              </span>
            </label>
            <label className="block">
              <span className="text-sm font-bold text-white/48">CVC</span>
              <span className="mt-3 flex h-14 items-center rounded-xl border border-white/14 bg-black/35 px-4 focus-within:border-emerald-400">
                <input
                  className="w-full bg-transparent text-base font-medium outline-none placeholder:text-white/35"
                  placeholder="123"
                />
              </span>
            </label>
          </div>
        </div>
      </div>

      <p className="flex items-center gap-3 text-sm font-bold text-white/34">
        Akzeptiert:
        <span className="text-white/70">VISA</span>
        <span className="text-white/70">Mastercard</span>
        <span className="text-white/70">PayPal</span>
      </p>
    </section>

    <section className="space-y-5">
      <OrderSummary deck={deck} selectedPackage={selectedPackage} />
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
          <LockKeyhole className="size-5" />
          {selectedPackage.price} EUR bezahlen
        </button>
      </div>
      <p className="text-sm font-medium text-white/32">
        Mit dem Klick stimmst du den AGB & Widerrufsbestimmungen zu.
      </p>
    </section>
  </div>
);

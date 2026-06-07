import { useState } from "react";
import type { ReactNode } from "react";
import {
  ArrowLeft,
  ArrowRight,
  Building2,
  Home,
  MapPin,
  TicketPercent,
  User,
} from "lucide-react";

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
}: ContactStepProps) => {
  const [hasDifferentBillingAddress, setHasDifferentBillingAddress] =
    useState(false);

  return (
    <div className="grid gap-10 lg:grid-cols-[minmax(0,1fr)_30rem]">
      <section className="space-y-8">
        <div>
          <h1 className="text-4xl font-black tracking-[-0.05em] text-white">
            Deine Adresse
          </h1>
          <p className="mt-4 max-w-3xl text-lg font-medium text-white/55">
            Deine Kontaktdaten haben wir bereits. Ergaenze hier die Adresse fuer
            Versand und Rechnung.
          </p>
        </div>

        <div className="rounded-3xl border border-white/10 bg-[#121718] p-8">
          <div className="flex gap-4">
            <span className="grid size-8 shrink-0 place-items-center rounded-full bg-white/8 text-sm font-black text-white/52">
              1
            </span>
            <div>
              <h2 className="text-xl font-black text-white">
                Versandadresse
              </h2>
              <p className="mt-2 text-base font-medium text-white/50">
                Fuer gedruckte Decks und die korrekte Rechnung.
              </p>
            </div>
          </div>

          <div className="mt-8 grid gap-5 sm:grid-cols-2">
            <AddressField
              icon={<User className="size-5" />}
              label="Vor- und Nachname"
              placeholder="Max Mustermann"
            />
            <AddressField
              icon={<Building2 className="size-5" />}
              label="Firma"
              placeholder="Optional"
            />
            <AddressField
              className="sm:col-span-2"
              icon={<Home className="size-5" />}
              label="Strasse und Hausnummer"
              placeholder="Musterstrasse 12"
            />
            <AddressField label="PLZ" placeholder="12345" />
            <AddressField label="Ort" placeholder="Berlin" />
            <AddressField
              className="sm:col-span-2"
              icon={<MapPin className="size-5" />}
              label="Land"
              placeholder="Deutschland"
            />
          </div>

          <label className="mt-7 flex cursor-pointer items-start gap-3 rounded-2xl border border-white/10 bg-black/20 p-4 text-left transition hover:border-white/18">
            <input
              checked={hasDifferentBillingAddress}
              className="mt-1 size-4 accent-emerald-400"
              type="checkbox"
              onChange={(event) =>
                setHasDifferentBillingAddress(event.target.checked)
              }
            />
            <span>
              <span className="block text-base font-black text-white">
                Abweichende Rechnungsadresse
              </span>
              <span className="mt-1 block text-sm font-medium text-white/45">
                Nur ausfuellen, wenn die Rechnung an eine andere Adresse gehen
                soll.
              </span>
            </span>
          </label>

          {hasDifferentBillingAddress ? (
            <div className="mt-6 border-t border-white/10 pt-6">
              <div className="flex gap-4">
                <span className="grid size-8 shrink-0 place-items-center rounded-full bg-white/8 text-sm font-black text-white/52">
                  2
                </span>
                <div>
                  <h2 className="text-xl font-black text-white">
                    Rechnungsadresse
                  </h2>
                  <p className="mt-2 text-base font-medium text-white/50">
                    Wenn abweichend von der Versandadresse.
                  </p>
                </div>
              </div>

              <div className="mt-8 grid gap-5 sm:grid-cols-2">
                <AddressField
                  icon={<User className="size-5" />}
                  label="Name / Firma"
                  placeholder="Max Mustermann GmbH"
                />
                <AddressField label="USt-IdNr." placeholder="Optional" />
                <AddressField
                  className="sm:col-span-2"
                  icon={<Home className="size-5" />}
                  label="Strasse und Hausnummer"
                  placeholder="Rechnungsstrasse 8"
                />
                <AddressField label="PLZ" placeholder="12345" />
                <AddressField label="Ort" placeholder="Berlin" />
                <AddressField
                  className="sm:col-span-2"
                  icon={<MapPin className="size-5" />}
                  label="Land"
                  placeholder="Deutschland"
                />
              </div>
            </div>
          ) : null}
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
      </section>
    </div>
  );
};

type AddressFieldProps = {
  className?: string;
  icon?: ReactNode;
  label: string;
  placeholder: string;
};

const AddressField = ({
  className,
  icon,
  label,
  placeholder,
}: AddressFieldProps) => (
  <label className={className}>
    <span className="text-sm font-bold text-white/48">{label}</span>
    <span className="mt-3 flex h-14 items-center gap-3 rounded-xl border border-white/14 bg-black/35 px-4 text-white/48 focus-within:border-emerald-400">
      {icon}
      <input
        className="w-full min-w-0 bg-transparent text-base font-medium outline-none placeholder:text-white/35"
        placeholder={placeholder}
      />
    </span>
  </label>
);

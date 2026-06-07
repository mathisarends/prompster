import { ArrowRight, Check, X } from "lucide-react";

import { cn } from "@/shared/lib/utils";

import type { CheckoutPackage } from "../types";

type PackageSelectorProps = {
  packages: CheckoutPackage[];
  selectedPackageId: string;
  onSelectPackage: (packageId: string) => void;
  onContinue: () => void;
};

export const PackageSelector = ({
  packages,
  selectedPackageId,
  onSelectPackage,
  onContinue,
}: PackageSelectorProps) => {
  const selectedPackage =
    packages.find(
      (checkoutPackage) => checkoutPackage.id === selectedPackageId,
    ) ?? packages[0];

  return (
    <section className="space-y-5">
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-white">
          Paket auswählen
        </h2>
        <p className="mt-1 text-base font-medium text-white/52">
          Einmalzahlung, kein Abo. Du behaeltst dein Deck fuer immer.
        </p>
      </div>

      <div className="grid gap-5 lg:grid-cols-3">
        {packages.map((checkoutPackage) => {
          const isSelected = checkoutPackage.id === selectedPackageId;

          return (
            <button
              key={checkoutPackage.id}
              type="button"
              onClick={() => onSelectPackage(checkoutPackage.id)}
              className={cn(
                "group relative flex min-h-[26rem] flex-col rounded-3xl border p-7 text-left transition duration-300",
                "bg-[#121718] hover:-translate-y-1 hover:border-emerald-300/55 hover:bg-[#151d1b]",
                isSelected
                  ? "border-emerald-400 bg-emerald-400/[0.085] shadow-[0_30px_90px_hsl(154_70%_36%/0.18)]"
                  : "border-white/10",
              )}
              aria-pressed={isSelected}
            >
              {checkoutPackage.isRecommended && checkoutPackage.badge ? (
                <span className="absolute -top-3 left-8 rounded-full bg-emerald-400 px-4 py-1.5 text-xs font-black uppercase tracking-wide text-[#06110d]">
                  {checkoutPackage.badge}
                </span>
              ) : null}

              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-base font-bold uppercase tracking-wide text-white/54">
                    {checkoutPackage.name}
                  </p>
                  <p className="mt-5 text-5xl font-black tracking-[-0.08em] text-white">
                    <span className="mr-1 text-2xl tracking-tight">EUR</span>
                    {checkoutPackage.price}
                  </p>
                </div>
                <span
                  className={cn(
                    "grid size-7 place-items-center rounded-full border transition",
                    isSelected
                      ? "border-emerald-400 bg-emerald-400 text-[#06110d]"
                      : "border-white/18 group-hover:border-emerald-300/65",
                  )}
                >
                  {isSelected ? <Check className="size-4" /> : null}
                </span>
              </div>

              <p className="mt-5 min-h-14 text-base font-medium leading-7 text-white/56">
                {checkoutPackage.title}
              </p>

              <ul className="mt-8 flex flex-1 flex-col gap-4">
                {checkoutPackage.features.map((feature) => (
                  <li
                    key={feature.label}
                    className={cn(
                      "flex items-center gap-3 text-base font-semibold",
                      feature.included ? "text-white/86" : "text-white/30",
                    )}
                  >
                    {feature.included ? (
                      <Check className="size-4 shrink-0 text-emerald-300" />
                    ) : (
                      <X className="size-4 shrink-0 text-white/28" />
                    )}
                    {feature.label}
                  </li>
                ))}
              </ul>
            </button>
          );
        })}
      </div>

      <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
        <button
          type="button"
          onClick={onContinue}
          className="group inline-flex w-full items-center justify-center gap-3 rounded-xl bg-emerald-400 px-8 py-4 text-lg font-black text-[#06110d] shadow-[0_24px_70px_hsl(154_70%_36%/0.22)] transition hover:-translate-y-0.5 hover:bg-emerald-300 sm:w-auto"
        >
          {selectedPackage.ctaLabel}
          <span>-</span>
          <span>{selectedPackage.price} EUR</span>
          <ArrowRight className="size-5 transition group-hover:translate-x-1" />
        </button>
        <p className="text-sm font-semibold text-white/34">
          {selectedPackage.note ?? "Sofort-Download - 14 Tage Geld-zurueck"}
        </p>
      </div>
    </section>
  );
};

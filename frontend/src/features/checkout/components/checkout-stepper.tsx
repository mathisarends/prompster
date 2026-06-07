import { Check } from "lucide-react";

import { cn } from "@/shared/lib/utils";

import type { CheckoutStep, CheckoutStepId } from "../types";

type CheckoutStepperProps = {
  steps: CheckoutStep[];
  currentStepId: CheckoutStepId;
};

export const CheckoutStepper = ({
  steps,
  currentStepId,
}: CheckoutStepperProps) => {
  const currentIndex = steps.findIndex((step) => step.id === currentStepId);

  return (
    <nav aria-label="Checkout Fortschritt" className="w-full">
      <ol className="flex flex-wrap items-center justify-center gap-3 text-sm font-semibold sm:gap-4">
        {steps.map((step, index) => {
          const isActive = step.id === currentStepId;
          const isCompleted = index < currentIndex;

          return (
            <li key={step.id} className="flex items-center gap-3 sm:gap-4">
              <div className="flex items-center gap-2.5">
                <span
                  className={cn(
                    "grid size-9 place-items-center rounded-full border text-sm transition-colors",
                    isActive
                      ? "border-emerald-400 bg-emerald-400/10 text-emerald-300 shadow-[0_0_0_5px_hsl(154_70%_45%/0.12)]"
                      : "border-white/16 bg-white/[0.03] text-white/42",
                    isCompleted && "border-emerald-400/60 text-emerald-300",
                  )}
                >
                  {isCompleted ? <Check className="size-4" /> : index + 1}
                </span>
                <span
                  className={cn(
                    "hidden tracking-tight sm:inline",
                    isActive ? "text-white" : "text-white/38",
                  )}
                >
                  {step.label}
                </span>
              </div>
              {index < steps.length - 1 ? (
                <span className="h-px w-8 bg-white/20 sm:w-11" aria-hidden />
              ) : null}
            </li>
          );
        })}
      </ol>
    </nav>
  );
};

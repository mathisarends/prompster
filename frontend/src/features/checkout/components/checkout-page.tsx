import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, LockKeyhole, Sparkles } from "lucide-react";

import { PrompsterLogo } from "@/shared/components/prompster-logo";

import {
  checkoutDeck,
  checkoutPackages,
  checkoutSteps,
} from "../data/mock-checkout";
import type { CheckoutStepId } from "../types";
import { CheckoutStepper } from "./checkout-stepper";
import { ContactStep } from "./contact-step";
import { DeckPreview } from "./deck-preview";
import { PackageSelector } from "./package-selector";
import { PaymentStep } from "./payment-step";
import { SuccessStep } from "./success-step";

const stepOrder: CheckoutStepId[] = ["package", "details", "payment", "done"];

export const CheckoutPage = () => {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState<CheckoutStepId>("package");
  const [selectedPackageId, setSelectedPackageId] = useState("plus");

  const selectedPackage =
    checkoutPackages.find(
      (checkoutPackage) => checkoutPackage.id === selectedPackageId,
    ) ?? checkoutPackages[0];

  const goToNextStep = () => {
    const currentIndex = stepOrder.indexOf(currentStep);
    setCurrentStep(stepOrder[Math.min(currentIndex + 1, stepOrder.length - 1)]);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const goToPreviousStep = () => {
    const currentIndex = stepOrder.indexOf(currentStep);
    setCurrentStep(stepOrder[Math.max(currentIndex - 1, 0)]);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const isSuccessStep = currentStep === "done";

  return (
    <div className="relative min-h-dvh overflow-hidden bg-[#070b0c] text-white">
      <div
        className="pointer-events-none absolute inset-0"
        aria-hidden
        style={{
          background:
            "radial-gradient(circle at 86% 9%, hsl(154 70% 30% / 0.18), transparent 30%), radial-gradient(circle at 12% 95%, hsl(154 55% 18% / 0.16), transparent 28%), linear-gradient(180deg, #090d0e 0%, #060808 100%)",
        }}
      />
      <div className="relative z-10 mx-auto flex min-h-dvh w-full max-w-[96rem] flex-col px-5 py-7 sm:px-8 lg:px-14">
        <header className="flex items-center justify-between gap-4">
          {currentStep === "package" || isSuccessStep ? (
            <PrompsterLogo
              iconClassName="size-10 rounded-xl bg-emerald-400 text-[#07110d] shadow-[0_0_35px_hsl(154_70%_44%/0.28)]"
              titleClassName="text-xl text-white"
              subtitle="Checkout"
              subtitleClassName="text-xl font-semibold text-white/28"
            />
          ) : (
            <button
              type="button"
              onClick={() => navigate("/new")}
              className="inline-flex items-center gap-2 rounded-xl bg-white/6 px-4 py-3 text-base font-black text-white/72 transition hover:bg-white/10 hover:text-white"
            >
              <ArrowLeft className="size-5" />
              Zurueck zum Deck
            </button>
          )}
          <div className="hidden items-center gap-2 rounded-full border border-white/12 bg-white/[0.035] px-4 py-2 text-sm font-semibold text-white/45 sm:flex">
            <LockKeyhole className="size-4 text-emerald-300" />
            Sichere Zahlung ueber Stripe
          </div>
        </header>

        {!isSuccessStep ? (
          <div className="mt-8 sm:mt-10">
            <CheckoutStepper
              steps={checkoutSteps}
              currentStepId={currentStep}
            />
          </div>
        ) : null}

        <main className="flex-1 pt-10 sm:pt-16">
          {currentStep === "package" ? (
            <>
              <section className="space-y-10">
                <div className="max-w-3xl space-y-5">
                  <div className="inline-flex items-center gap-2 text-sm font-bold uppercase tracking-[0.16em] text-emerald-300">
                    <Sparkles className="size-4" />
                    Fast fertig
                  </div>
                  <div className="space-y-4">
                    <h1 className="max-w-2xl text-5xl font-bold leading-[0.98] tracking-[-0.055em] text-white sm:text-6xl">
                      Dein Deck ist bereit. Wähle dein Paket.
                    </h1>
                    <p className="max-w-2xl text-lg font-medium leading-8 text-white/55 sm:text-xl">
                      Lade dein persoenliches Hitster-Deck als druckfertiges PDF
                      herunter - oder lass es gedruckt zu dir nach Hause
                      schicken.
                    </p>
                  </div>
                </div>
                <DeckPreview deck={checkoutDeck} />
              </section>

              <div className="mt-10 sm:mt-14">
                <PackageSelector
                  packages={checkoutPackages}
                  selectedPackageId={selectedPackageId}
                  onSelectPackage={setSelectedPackageId}
                  onContinue={goToNextStep}
                />
              </div>
            </>
          ) : null}

          {currentStep === "details" ? (
            <ContactStep
              deck={checkoutDeck}
              selectedPackage={selectedPackage}
              onBack={goToPreviousStep}
              onContinue={goToNextStep}
            />
          ) : null}

          {currentStep === "payment" ? (
            <PaymentStep
              deck={checkoutDeck}
              selectedPackage={selectedPackage}
              onBack={goToPreviousStep}
              onContinue={goToNextStep}
            />
          ) : null}

          {currentStep === "done" ? (
            <SuccessStep
              deck={checkoutDeck}
              selectedPackage={selectedPackage}
              onRestart={() => navigate("/new")}
            />
          ) : null}
        </main>
      </div>
    </div>
  );
};

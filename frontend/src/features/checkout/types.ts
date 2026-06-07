export type CheckoutStepId = "package" | "details" | "payment" | "done";

export type CheckoutStep = {
  id: CheckoutStepId;
  label: string;
};

export type CheckoutDeckCard = {
  id: string;
  seed: number;
  year: string;
  title: string;
  artist: string;
};

export type CheckoutDeck = {
  title: string;
  cardCount: number;
  meta: string[];
  previewCards: CheckoutDeckCard[];
  lockedCardsLabel: string;
};

export type CheckoutPackage = {
  id: string;
  name: string;
  title: string;
  description: string;
  price: string;
  ctaLabel: string;
  note?: string;
  isSelected?: boolean;
  isRecommended?: boolean;
  badge?: string;
  features: Array<{
    label: string;
    included: boolean;
  }>;
};

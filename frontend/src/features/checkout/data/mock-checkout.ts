import type { CheckoutDeck, CheckoutPackage, CheckoutStep } from "../types";

export const checkoutSteps: CheckoutStep[] = [
  { id: "package", label: "Paket" },
  { id: "details", label: "Daten" },
  { id: "payment", label: "Bezahlung" },
  { id: "done", label: "Fertig" },
];

export const checkoutDeck: CheckoutDeck = {
  title: "Querbeet-Mix 70-20er",
  cardCount: 50,
  meta: ["QR zum Scannen", "1977-2022"],
  previewCards: [
    {
      id: "card-1",
      seed: 6,
      year: "1977",
      title: "Heroes",
      artist: "David Bowie",
    },
    {
      id: "card-2",
      seed: 13,
      year: "2008",
      title: "Haus am See",
      artist: "Peter Fox",
    },
    {
      id: "card-3",
      seed: 22,
      year: "1991",
      title: "Losing My Religion",
      artist: "R.E.M.",
    },
    {
      id: "card-4",
      seed: 31,
      year: "2019",
      title: "Blinding Lights",
      artist: "The Weeknd",
    },
    {
      id: "card-5",
      seed: 44,
      year: "1983",
      title: "99 Luftballons",
      artist: "Nena",
    },
  ],
  lockedCardsLabel: "+45 Karten",
};

export const checkoutPackages: CheckoutPackage[] = [
  {
    id: "basic",
    name: "Basic",
    title: "Schnell gedruckt fuer den naechsten Spieleabend.",
    description: "Einmalzahlung, kein Abo. Du behaeltst dein Deck fuer immer.",
    price: "4,99",
    ctaLabel: "Basic auswählen",
    features: [
      { label: "20 Spielkarten", included: true },
      { label: "Digitales PDF (A4)", included: true },
      { label: "Sofort-Download", included: true },
      { label: "Spotify-Playlist inklusive", included: true },
      { label: "Druckhilfen & Schnittmarken", included: false },
      { label: "Gedruckt & per Post", included: false },
    ],
  },
  {
    id: "plus",
    name: "Plus",
    title:
      "Volles Deck zum Selberdrucken - bestes Preis-Leistungs-Verhaeltnis.",
    description: "Einmalzahlung, kein Abo. Du behaeltst dein Deck fuer immer.",
    price: "9,99",
    ctaLabel: "Weiter zur Bestellung",
    note: "Sofort-Download · 14 Tage Geld-zurueck",
    isSelected: true,
    isRecommended: true,
    badge: "Beliebteste Wahl",
    features: [
      { label: "50 Spielkarten", included: true },
      { label: "Hochaufloesendes Druck-PDF", included: true },
      { label: "Doppelseitig, mit Schnitt- & Falzhilfen", included: true },
      { label: "Spotify-Playlist inklusive", included: true },
      { label: "Lebenslange Updates des Decks", included: true },
      { label: "Gedruckt & per Post", included: false },
    ],
  },
  {
    id: "premium",
    name: "Premium",
    title: "Fertig gedruckt auf stabilem Karton - direkt in den Briefkasten.",
    description: "Einmalzahlung, kein Abo. Du behältst dein Deck für immer.",
    price: "24,99",
    ctaLabel: "Premium auswählen",
    features: [
      { label: "50 Spielkarten", included: true },
      { label: "Professionell gedruckt", included: true },
      { label: "Stabiler 350g Karton, matt", included: true },
      { label: "Versand per Post (3-5 Werktage)", included: true },
      { label: "Digitales PDF gratis dazu", included: true },
      { label: "Spotify-Playlist inklusive", included: true },
    ],
  },
];

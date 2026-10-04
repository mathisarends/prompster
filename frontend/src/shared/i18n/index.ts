import { configureLocalization, type LocaleModule } from "@lit/localize";
import { sourceLocale, targetLocales } from "./locale-codes";
import { localeStorageKey, preferredLocale } from "./locale";

const modules = import.meta.glob<LocaleModule>("./generated/*.ts");
const localization = configureLocalization({
  sourceLocale,
  targetLocales,
  loadLocale: async (locale) => {
    const load = modules[`./generated/${locale}.ts`];
    if (!load) {
      throw new Error(`Unsupported locale: ${locale}`);
    }
    return load();
  },
});

export const getLocale = localization.getLocale;

export async function setLocale(locale: string): Promise<void> {
  try {
    await localization.setLocale(locale);
  } catch (error) {
    // Reset Lit Localize's failed loading state so a later attempt can retry.
    await localization.setLocale(getLocale());
    throw error;
  }
  // Only persist the active locale, including when requests finish out of order.
  document.documentElement.lang = getLocale();
  try {
    localStorage.setItem(localeStorageKey, getLocale());
  } catch {
    // Storage can be unavailable in privacy mode; switching still works.
  }
}

export async function initializeLocale(): Promise<void> {
  let saved: string | null = null;
  try {
    saved = localStorage.getItem(localeStorageKey);
  } catch {
    // Use the browser preference when storage is unavailable.
  }
  try {
    await localization.setLocale(preferredLocale(saved, navigator.languages));
  } catch {
    // A failed locale download must not prevent the app from starting.
    await localization.setLocale(sourceLocale);
  }
  document.documentElement.lang = getLocale();
}

export function formatDate(value: string | Date): string {
  return new Intl.DateTimeFormat(getLocale(), {
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(new Date(value));
}

export function formatNumber(value: number): string {
  return new Intl.NumberFormat(getLocale()).format(value);
}

export function speechLocale(): string {
  return getLocale() === "de" ? "de-DE" : "en-US";
}

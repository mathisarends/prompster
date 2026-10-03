import { allLocales, sourceLocale } from "./locale-codes";

export const localeStorageKey = "prompster.locale";

/** Match regional browser preferences (en-GB, de-AT) to supported languages. */
export function matchLocale(value: string | null | undefined): string | undefined {
  const language = value?.toLowerCase().split(/[-_]/)[0];
  return allLocales.find((locale) => locale === language);
}

export function preferredLocale(saved: string | null, languages: readonly string[]): string {
  return matchLocale(saved) ?? languages.map(matchLocale).find(Boolean) ?? sourceLocale;
}

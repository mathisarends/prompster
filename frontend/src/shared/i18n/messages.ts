import { msg, str } from "@lit/localize";
import { formatNumber, getLocale } from "./index";

export function cardCount(count: number): string {
  const value = formatNumber(count);
  return new Intl.PluralRules(getLocale()).select(count) === "one"
    ? msg(str`${value} Erinnerung auf einer Karte`)
    : msg(str`${value} Erinnerungen auf Karten`);
}

export function researchStepCount(count: number): string {
  const value = formatNumber(count);
  return new Intl.PluralRules(getLocale()).select(count) === "one"
    ? msg(str`${value} Recherche-Schritt`)
    : msg(str`${value} Recherche-Schritte`);
}

export function deleteAccountDescription(count: number): string {
  const value = formatNumber(count);
  return new Intl.PluralRules(getLocale()).select(count) === "one"
    ? msg(str`${value} Deck mit seiner Unterhaltung wird zusammen mit deinem Konto gelöscht.`)
    : msg(str`${value} Decks mit ihren Unterhaltungen werden zusammen mit deinem Konto gelöscht.`);
}

export function retryLabel(attempt: number, maxAttempts: number): string {
  return msg(str`Versuch ${formatNumber(attempt)}/${formatNumber(maxAttempts)}`);
}

export function emit<T>(target: EventTarget, type: string, detail?: T): boolean {
  return target.dispatchEvent(new CustomEvent(type, { detail, bubbles: true, composed: true }));
}
export function errorMessage(error: unknown): string {
  return error instanceof Error
    ? error.message
    : "Etwas ist schiefgelaufen. Bitte versuche es erneut.";
}

import { msg } from "@lit/localize";

export function speechErrorMessage(code: string): string {
  switch (code) {
    case "not-allowed":
      return msg("Bitte den Mikrofonzugriff im Browser erlauben.");
    case "service-not-allowed":
      return msg("Die Spracherkennung ist in diesem Browser nicht freigegeben.");
    case "audio-capture":
      return msg("Kein verfügbares Mikrofon gefunden.");
    case "no-speech":
      return msg("Keine Sprache erkannt. Bitte erneut versuchen.");
    case "network":
      return msg("Keine Verbindung zur Spracherkennung. Bitte erneut versuchen.");
    default:
      return msg("Diktieren ist gerade nicht möglich. Bitte erneut versuchen.");
  }
}

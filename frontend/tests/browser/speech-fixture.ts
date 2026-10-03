import type { Page } from "@playwright/test";
import type {
  BrowserSpeechRecognition,
  SpeechConstructor,
} from "../../src/shared/ui/voice-input/speech-session";

export type SpeechTestWindow = Window & {
  SpeechRecognition?: SpeechConstructor;
  webkitSpeechRecognition?: SpeechConstructor;
  speechInstances: (BrowserSpeechRecognition & { aborted: boolean; result(text: string): void })[];
};

/** Browser-recognition fixture only; never requests the actual microphone. */
export async function mockSpeech(page: Page, supported = true): Promise<void> {
  await page.addInitScript((supported) => {
    const browser = window as SpeechTestWindow;
    browser.speechInstances = [];
    browser.webkitSpeechRecognition = undefined;
    browser.SpeechRecognition = supported
      ? class {
          lang = "";
          continuous = false;
          interimResults = false;
          aborted = false;
          onstart: BrowserSpeechRecognition["onstart"] = null;
          onresult: BrowserSpeechRecognition["onresult"] = null;
          onerror: BrowserSpeechRecognition["onerror"] = null;
          onend: BrowserSpeechRecognition["onend"] = null;
          constructor() {
            browser.speechInstances.push(this);
          }
          start() {
            this.onstart?.();
          }
          stop() {
            this.onend?.();
          }
          abort() {
            this.aborted = true;
          }
          result(text: string) {
            this.onresult?.({ results: [[{ transcript: text }]] });
          }
        }
      : undefined;
  }, supported);
}

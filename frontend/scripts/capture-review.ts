import { chromium, expect, type Page } from "@playwright/test";
import { mkdir, rename, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { mockApi, session } from "../tests/browser/fixtures";
import { mockSpeech, type SpeechTestWindow } from "../tests/browser/speech-fixture";

const output = fileURLToPath(new URL("../../docs/reviews/lit-frontend/", import.meta.url));
const raw = fileURLToPath(new URL("../test-results/review-raw/", import.meta.url));
await mkdir(output, { recursive: true });
await mkdir(raw, { recursive: true });
const browser = await chromium.launch({
  channel: process.platform === "win32" ? "chrome" : undefined,
});
const baseURL = process.env.REVIEW_BASE_URL ?? "http://127.0.0.1:5175";

const demo = session();
demo.title = "Unser Spieleabend";
demo.playlist.name = "Klassiker für den Spieleabend";
demo.playlist.tracks = [
  { ...demo.playlist.tracks[0] },
  {
    id: "track-2",
    title: "Smells Like Teen Spirit",
    artist: "Nirvana",
    year: 1991,
    spotifyUri: "spotify:track:track-2",
    coverUrl: null,
  },
  {
    id: "track-3",
    title: "Wannabe",
    artist: "Spice Girls",
    year: 1996,
    spotifyUri: "spotify:track:track-3",
    coverUrl: null,
  },
  {
    id: "track-4",
    title: "One More Time",
    artist: "Daft Punk",
    year: 2000,
    spotifyUri: "spotify:track:track-4",
    coverUrl: null,
  },
];
demo.entries[0].content =
  "Ein gemischtes Deck mit Klassikern aus den 70ern, 90ern und 2000ern für unseren Spieleabend.";
demo.entries[1].content =
  "Hier ist dein **Spieleabend-Deck**: vier bekannte Songs aus drei Jahrzehnten.\n\n- **1976** · Disco zum Warmwerden\n- **1991 & 1996** · Zwei Seiten der 90er\n- **2000** · Ein elektronischer Klassiker\n\nIm Deckbereich kannst du die Karten ansehen, die Jahreszahlen verdecken und dein Deck exportieren.";

const pause = (ms = 1300) => new Promise((resolve) => setTimeout(resolve, ms));
async function shot(page: Page, name: string) {
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({ path: `${output}${name}.png`, animations: "disabled" });
}
const failures: string[] = [];
const watch = (page: Page) => page.on("pageerror", (error) => failures.push(error.message));

try {
  const loginContext = await browser.newContext({
    viewport: { width: 1440, height: 960 },
    locale: "de-DE",
    reducedMotion: "reduce",
  });
  const login = await loginContext.newPage();
  watch(login);
  await mockApi(login, false);
  await login.goto(baseURL);
  await expect(login.getByRole("button", { name: "Mit Spotify fortfahren" })).toBeVisible();
  await shot(login, "01-login-desktop");
  await loginContext.close();

  const desktopContext = await browser.newContext({
    viewport: { width: 1440, height: 960 },
    locale: "de-DE",
    recordVideo: { dir: raw, size: { width: 1440, height: 960 } },
  });
  const desktop = await desktopContext.newPage();
  watch(desktop);
  await mockApi(desktop, true, false, demo);
  await mockSpeech(desktop);
  await desktop.goto(`${baseURL}/new`);
  await expect(desktop.locator("studio-page")).toBeVisible();
  await shot(desktop, "02-studio-desktop");
  await pause(1800);
  await desktop.getByRole("button", { name: "Diktieren", exact: true }).click();
  await desktop.evaluate(() =>
    (window as SpeechTestWindow).speechInstances
      .at(-1)!
      .result("Ein Kartendeck mit Musik aus den Neunzigern für unseren Spieleabend."),
  );
  await shot(desktop, "13-dictation-desktop");
  await pause(2100);
  await desktop.getByRole("button", { name: "Text übernehmen" }).click();
  await pause(1000);
  await desktop.getByRole("button", { name: /Zurück in die 90er/ }).click();
  await pause(1500);
  await desktop.getByRole("button", { name: "Nachricht senden", exact: true }).click();
  await expect(desktop).toHaveURL(/\/chat\/new-deck/);
  await expect(desktop.locator("deck-panel")).toContainText("Wannabe");
  await expect(desktop.getByRole("textbox", { name: "Nachricht", exact: true })).toHaveValue("");
  await shot(desktop, "03-chat-playlist-desktop");
  await pause(2600);
  await desktop.getByRole("tab", { name: "Karten", exact: true }).click();
  await shot(desktop, "04-cards-desktop");
  await pause(2100);
  await desktop.getByRole("checkbox", { name: "Auflösung verbergen" }).check();
  await shot(desktop, "11-qr-desktop");
  await pause(1800);
  await desktop.getByRole("checkbox", { name: "Auflösung verbergen" }).uncheck();
  await desktop.getByRole("button", { name: "Deck vergrößern" }).click();
  await shot(desktop, "12-workspace-expanded");
  await pause(1700);
  await desktop.getByRole("button", { name: "Geteilte Ansicht" }).click();
  await pause(700);
  await desktop.getByRole("tab", { name: "Export", exact: true }).click();
  await shot(desktop, "05-export-desktop");
  await pause(1800);
  await desktop.getByRole("button", { name: "Meine Decks", exact: true }).click();
  await expect(desktop.locator("library-page")).toContainText("Unser Spieleabend");
  await shot(desktop, "06-library-desktop");
  await pause(1700);
  await desktop.getByRole("button", { name: /Mathi Dein Deckstudio/ }).click();
  await expect(desktop.getByRole("heading", { name: "Einstellungen", exact: true })).toBeVisible();
  await shot(desktop, "07-settings-desktop");
  await pause(1800);
  const desktopVideo = desktop.video()!;
  await desktopContext.close();
  await rename(await desktopVideo.path(), `${raw}desktop.webm`);

  const mobileContext = await browser.newContext({
    viewport: { width: 390, height: 844 },
    locale: "de-DE",
    isMobile: true,
    hasTouch: true,
    deviceScaleFactor: 1,
    recordVideo: { dir: raw, size: { width: 390, height: 844 } },
  });
  const mobile = await mobileContext.newPage();
  watch(mobile);
  await mockApi(mobile, true, false, demo);
  await mockSpeech(mobile);
  await mobile.goto(`${baseURL}/new`);
  await expect(mobile.locator("studio-page")).toBeVisible();
  await shot(mobile, "08-studio-mobile");
  await pause(1800);
  await mobile.getByRole("button", { name: "Diktieren", exact: true }).click();
  await mobile.evaluate(() =>
    (window as SpeechTestWindow).speechInstances
      .at(-1)!
      .result("Ein Mix aus Disco und Neunziger-Hits."),
  );
  await shot(mobile, "14-dictation-mobile");
  await pause(2000);
  await mobile.getByRole("button", { name: "Diktat verwerfen" }).click();
  await mobile.getByRole("button", { name: "Seitenleiste öffnen" }).click();
  await pause(1300);
  await mobile.getByRole("button", { name: "Unser Spieleabend", exact: true }).click();
  await expect(mobile.locator("assistant-message")).toContainText("Spieleabend-Deck");
  await shot(mobile, "09-chat-mobile");
  await pause(2000);
  await mobile.getByRole("button", { name: /Dein Deck/ }).click();
  await expect(mobile.locator("deck-panel")).toBeVisible();
  await pause(1700);
  await mobile.getByRole("tab", { name: "Karten", exact: true }).click();
  await shot(mobile, "10-cards-mobile");
  await pause(2200);
  await mobile.getByRole("checkbox", { name: "Auflösung verbergen" }).check();
  await pause(1400);
  await mobile.getByRole("button", { name: "Deck schließen", exact: true }).click();
  await expect(mobile.getByRole("textbox", { name: "Nachricht", exact: true })).toBeVisible();
  await pause(1200);
  if (await mobile.evaluate(() => document.documentElement.scrollWidth > innerWidth)) {
    throw new Error("Mobile view overflows horizontally");
  }
  const mobileVideo = mobile.video()!;
  await mobileContext.close();
  await rename(await mobileVideo.path(), `${raw}mobile.webm`);
  if (failures.length) {
    throw new Error(failures.join("\n"));
  }
  await writeFile(
    `${raw}capture.json`,
    JSON.stringify(
      {
        desktop: "1440×960",
        mobile: "390×844",
        screenshots: 14,
        browserErrors: failures,
        fixture:
          "Local HTTP, WebSocket and SpeechRecognition mocks; no external account actions or microphone capture",
      },
      null,
      2,
    ),
  );
  process.stdout.write(
    `Captured 14 screenshots and 2 recordings in ${output}\nRaw recordings: ${raw}\n`,
  );
} finally {
  await browser.close();
}

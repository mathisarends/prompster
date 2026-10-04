import { test, expect } from "@playwright/test";
import { mockApi } from "./fixtures";
import { mockSpeech, type SpeechTestWindow } from "./speech-fixture";

test("language switching preserves a draft, deck tabs and content, then persists on reload", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await mockApi(page);
  await page.goto("/chat/deck-1");
  await page.getByRole("textbox", { name: "Nachricht", exact: true }).fill("Mein eigener Entwurf");
  await page.getByRole("tab", { name: "Karten", exact: true }).click();
  await page.getByRole("checkbox", { name: "Auflösung verbergen" }).check();
  await page.keyboard.press("ControlOrMeta+,");
  await page.getByRole("combobox", { name: "Sprache" }).selectOption("en");
  await page.getByRole("button", { name: "Unser Spieleabend", exact: true }).click();
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await expect(page).toHaveTitle("Deck studio · Prompster");
  await expect(page.getByRole("tab", { name: "Cards", exact: true })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  await expect(page.getByRole("checkbox", { name: "Hide answers" })).toBeChecked();
  await expect(page.getByRole("textbox", { name: "Message", exact: true })).toHaveValue(
    "Mein eigener Entwurf",
  );
  await expect(page.locator("side-bar language-select")).toHaveCount(0);
  await expect(page.locator("human-message")).toContainText("Ein Deck voller Klassiker");
  await expect(page.getByRole("img", { name: "Spotify QR code" })).toBeVisible();
  await expect(page.getByRole("button", { name: "So wird gespielt" })).toHaveCount(0);
  await expect(page.locator(".reference-button")).toHaveCount(0);
  await expect(page.locator("chat-page .toolbar")).toHaveCSS("border-bottom-width", "0px");
  await expect(page.locator("deck-panel header")).toHaveCSS("border-bottom-width", "0px");
  await page.reload();
  await expect(page.getByRole("button", { name: "My decks", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "My decks", exact: true }).click();
  await expect(page.locator("library-page")).toContainText("October");
  await page.keyboard.press("ControlOrMeta+,");
  await page.getByRole("combobox", { name: "Language" }).selectOption("de");
  await page.getByRole("button", { name: "Meine Decks", exact: true }).click();
  await expect(page.locator("library-page")).toContainText("Oktober");
  await expect(page).toHaveTitle("Meine Decks · Prompster");
  expect(errors).toEqual([]);
});

test("English browser preference localizes login, starters and export actions", async ({
  browser,
}) => {
  const context = await browser.newContext({ locale: "en-GB" });
  const page = await context.newPage();
  await mockApi(page, false);
  await page.goto("/");
  await expect(page.getByRole("button", { name: "Continue with Spotify" })).toBeVisible();
  await expect(page.getByRole("heading")).toHaveText("Turn favorite songsinto game nights.");
  await expect(page.getByRole("combobox", { name: "Language" })).toHaveCount(0);
  await mockApi(page);
  await page.goto("/new");
  await page.getByRole("button", { name: /Back to the 90s/ }).click();
  await expect(page.getByRole("button", { name: /Back to the 90s/ })).toContainText(
    "Boy bands, Britpop and big emotions",
  );
  await expect(page.getByRole("textbox", { name: "Message", exact: true })).toHaveValue(
    /A deck of the biggest 90s hits/,
  );
  await page.keyboard.press("ControlOrMeta+,");
  await page.getByRole("combobox", { name: "Language" }).selectOption("de");
  await page.getByRole("button", { name: /Neues Deck/ }).click();
  await expect(page.getByRole("button", { name: /Zurück in die 90er/ })).toBeVisible();
  await expect(page.getByRole("textbox", { name: "Nachricht", exact: true })).toHaveValue(
    /A deck of the biggest 90s hits/,
  );
  await page.keyboard.press("ControlOrMeta+,");
  await page.getByRole("combobox", { name: "Sprache" }).selectOption("en");
  await page.getByRole("button", { name: "Unser Spieleabend", exact: true }).click();
  await page.getByRole("tab", { name: "Export", exact: true }).click();
  await expect(page.getByRole("button", { name: "Download PDF", exact: true })).toBeEnabled();
  await expect(page.getByRole("button", { name: "Export to Spotify", exact: true })).toBeEnabled();
  await context.close();
});

test("settings stop dictation and the next recording uses the selected language", async ({
  page,
}) => {
  await mockApi(page);
  await mockSpeech(page);
  await page.goto("/new");
  await page.getByRole("button", { name: "Diktieren", exact: true }).click();
  expect(await page.evaluate(() => (window as SpeechTestWindow).speechInstances.at(-1)!.lang)).toBe(
    "de-DE",
  );
  await page.evaluate(() =>
    (window as SpeechTestWindow).speechInstances.at(-1)!.result("Nicht übernehmen"),
  );
  await page.keyboard.press("ControlOrMeta+,");
  await expect(page.getByRole("heading", { name: "Einstellungen", exact: true })).toBeVisible();
  expect(
    await page.evaluate(() => (window as SpeechTestWindow).speechInstances.at(-1)!.aborted),
  ).toBe(true);
  await page.getByRole("combobox", { name: "Sprache" }).selectOption("en");
  await page.getByRole("button", { name: /New deck/ }).click();
  await expect(page.getByRole("textbox", { name: "Message", exact: true })).toHaveValue("");
  await page.getByRole("button", { name: "Dictate", exact: true }).click();
  expect(await page.evaluate(() => (window as SpeechTestWindow).speechInstances.at(-1)!.lang)).toBe(
    "en-US",
  );
  await page.evaluate(() =>
    (window as SpeechTestWindow).speechInstances.at(-1)!.onerror?.({ error: "not-allowed" }),
  );
  await expect(page.getByRole("alert")).toContainText("Please allow microphone access");
  await page.getByRole("button", { name: "Dictate", exact: true }).click();
  await page.evaluate(() =>
    (window as SpeechTestWindow).speechInstances.at(-1)!.result("A deck of disco songs"),
  );
  await page.getByRole("button", { name: "Use text", exact: true }).click();
  await expect(page.getByRole("textbox", { name: "Message", exact: true })).toHaveValue(
    "A deck of disco songs",
  );
});

test("an unavailable locale falls back without breaking login or persisting the failed choice", async ({
  browser,
}) => {
  const context = await browser.newContext({ locale: "en-US" });
  const page = await context.newPage();
  await mockApi(page, false);
  await page.route("**/src/shared/i18n/generated/en.ts*", (route) => route.abort());
  await page.goto("/");
  await expect(page.getByRole("button", { name: "Mit Spotify fortfahren" })).toBeVisible();
  await expect(page.locator("html")).toHaveAttribute("lang", "de");
  await mockApi(page);
  await page.goto("/settings");
  await page.getByRole("combobox", { name: "Sprache" }).selectOption("en");
  await expect(page.getByRole("alert")).toContainText("Die Sprache konnte nicht geladen werden");
  await expect(page.getByRole("combobox", { name: "Sprache" })).toHaveValue("de");
  expect(await page.evaluate(() => localStorage.getItem("prompster.locale"))).toBeNull();
  await context.close();
});

test("unavailable storage still allows language switching on mobile", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.addInitScript(() => {
    Storage.prototype.getItem = () => {
      throw new DOMException("Blocked", "SecurityError");
    };
    Storage.prototype.setItem = () => {
      throw new DOMException("Blocked", "SecurityError");
    };
  });
  await mockApi(page);
  await page.goto("/new");
  await page.getByRole("button", { name: "Seitenleiste öffnen" }).click();
  await page.getByRole("button", { name: /Mathi Dein Deckstudio/ }).click();
  await page.getByRole("combobox", { name: "Sprache" }).selectOption("en");
  await page.getByRole("button", { name: "Open sidebar" }).click();
  await page.getByRole("button", { name: /New deck/ }).click();
  await expect(page.getByRole("button", { name: /Back to the 90s/ })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

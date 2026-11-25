import { test, expect } from "@playwright/test";
import { mockApi } from "./fixtures";
import { mockSpeech, type SpeechTestWindow } from "./speech-fixture";

test("workspace spans the viewport and supports keyboard tabs and expansion", async ({ page }) => {
  await mockApi(page);
  await page.setViewportSize({ width: 1440, height: 960 });
  await page.goto("/chat/deck-1");
  const panel = page.locator("deck-panel");
  await expect(panel).toBeVisible();
  const bounds = await panel.boundingBox();
  expect(bounds?.y).toBe(0);
  expect(bounds?.height).toBe(960);
  await page.getByRole("tab", { name: "Playlist", exact: true }).focus();
  await page.keyboard.press("ArrowRight");
  await expect(page.getByRole("tab", { name: "Karten", exact: true })).toBeFocused();
  const card = panel.locator("music-card article").first();
  await expect(card).toContainText("1976");
  await expect(card).toContainText("LP · 33⅓ RPM");
  const cardBox = await card.boundingBox();
  expect(Math.abs(cardBox!.width - cardBox!.height)).toBeLessThan(1);
  await page.getByRole("checkbox", { name: "Auflösung verbergen" }).check();
  await expect(card).not.toContainText("Dancing Queen");
  await expect(card).not.toContainText("RPM");
  await expect(card.getByRole("img", { name: "Spotify-QR-Code" })).toBeVisible();
  await page.getByRole("button", { name: "Deck vergrößern" }).click();
  await expect(page.getByRole("textbox", { name: "Nachricht", exact: true })).toBeHidden();
  expect((await panel.boundingBox())!.width).toBeGreaterThan(bounds!.width);
  await page.getByRole("button", { name: "Geteilte Ansicht" }).click();
  await expect(page.getByRole("textbox", { name: "Nachricht", exact: true })).toBeVisible();
});

test("cards turn over on hover and keep a concealed answer out of the page", async ({ page }) => {
  await mockApi(page);
  await page.setViewportSize({ width: 1440, height: 960 });
  await page.goto("/chat/deck-1");
  await page.getByRole("tab", { name: "Karten", exact: true }).click();
  await page.getByRole("checkbox", { name: "Auflösung verbergen" }).check();
  const card = page.locator("deck-panel music-card").first();
  await expect(card).not.toContainText("Dancing Queen");
  await card.hover();
  await expect(card.locator(".lift")).toHaveClass(/raised/);
  await expect(card.locator(".back")).toContainText("Dancing Queen");
  await expect(card.locator(".back")).toHaveAttribute("aria-hidden", "true");
  await page.mouse.move(0, 0);
  await expect(card.locator(".back")).toHaveCount(0);
  await expect(card).not.toContainText("Dancing Queen");
});

test("icon shortcut hints match actions, restore focus and respect settings and dialogs", async ({
  page,
}) => {
  await mockApi(page);
  await page.goto("/chat/deck-1");
  const panel = page.locator("deck-panel");
  const close = page.getByRole("button", { name: "Deck schließen", exact: true });
  await expect(close).toHaveAttribute("title", "Deck schließen · Alt+Shift+D");
  await expect(close).toHaveAttribute("aria-keyshortcuts", "Alt+Shift+D");
  await expect(page.locator("chat-page .toolbar")).not.toContainText("Deck schließen");
  await page.keyboard.press("Alt+Shift+d");
  const open = page.getByRole("button", { name: "Deck öffnen", exact: true });
  await expect(open).toBeFocused();
  await expect(panel).toHaveCount(0);
  await page.keyboard.press("Alt+Shift+d");
  await expect(page.getByRole("tab", { name: "Playlist", exact: true })).toBeFocused();
  await expect(page.getByRole("button", { name: "Deck vergrößern" })).toHaveAttribute(
    "title",
    "Deck vergrößern · Alt+Shift+F",
  );
  await page.keyboard.press("Alt+Shift+f");
  await expect(page.getByRole("textbox", { name: "Nachricht", exact: true })).toBeHidden();
  await page.keyboard.press("Alt+Shift+f");
  await expect(page.getByRole("textbox", { name: "Nachricht", exact: true })).toBeVisible();
  await page.keyboard.press("ControlOrMeta+b");
  await expect(page.locator("side-bar")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Seitenleiste öffnen" })).toHaveAttribute(
    "title",
    /(?:Ctrl|⌘)\+B/,
  );
  await page.keyboard.press("ControlOrMeta+b");
  await page.keyboard.press("ControlOrMeta+,");
  await expect(page).toHaveURL(/\/settings$/);
  await expect(panel).toBeHidden();
  await page.keyboard.press("Alt+Shift+d");
  await page.getByRole("button", { name: "Unser Spieleabend", exact: true }).click();
  await expect(panel).toBeVisible();
  await page.getByRole("button", { name: "Aktionen für Unser Spieleabend" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Alt+n");
  await page.keyboard.press("ControlOrMeta+,");
  await page.keyboard.press("Alt+Shift+d");
  await expect(page).toHaveURL(/\/chat\/deck-1$/);
  await expect(panel).toBeVisible();
  await page.keyboard.press("Escape");
  await page.keyboard.press("Alt+n");
  await expect(page).toHaveURL(/\/new$/);
  await expect(page.getByRole("button", { name: "Nachricht senden", exact: true })).toHaveAttribute(
    "title",
    "Nachricht senden · Enter",
  );
});

test("dictation previews, cancels and appends text without submitting it", async ({ page }) => {
  const api = await mockApi(page);
  await mockSpeech(page);
  await page.goto("/new");
  const composer = page.getByRole("textbox", { name: "Nachricht", exact: true });
  await composer.fill("Ein Deck mit");
  await page.getByRole("button", { name: "Diktieren", exact: true }).click();
  await page.evaluate(() => (window as SpeechTestWindow).speechInstances.at(-1)!.result("Disco"));
  await expect(composer).toHaveValue("Ein Deck mit Disco");
  await expect(composer).toHaveAttribute("readonly", "");
  await expect(page.getByRole("button", { name: "Diktat verwerfen" })).toHaveAttribute(
    "title",
    "Diktat verwerfen · Esc",
  );
  await page.getByRole("button", { name: "Diktat verwerfen" }).focus();
  await page.keyboard.press("Escape");
  await expect(composer).toHaveValue("Ein Deck mit");
  await page.getByRole("button", { name: "Diktieren", exact: true }).click();
  await page.evaluate(() =>
    (window as SpeechTestWindow).speechInstances.at(-1)!.result("Songs aus den Neunzigern"),
  );
  await page.getByRole("button", { name: "Text übernehmen" }).click();
  await expect(composer).toHaveValue("Ein Deck mit Songs aus den Neunzigern");
  await expect(composer).toBeFocused();
  expect(api.messages).toEqual([]);
  await page.getByRole("button", { name: "Diktieren", exact: true }).click();
  await page.evaluate(() =>
    (window as SpeechTestWindow).speechInstances.at(-1)!.result("nicht übernehmen"),
  );
  await page.getByRole("button", { name: "Unser Spieleabend", exact: true }).click();
  await expect(composer).toHaveValue("");
  expect(
    await page.evaluate(() => (window as SpeechTestWindow).speechInstances.at(-1)!.aborted),
  ).toBe(true);
});

test("speech permission errors preserve the draft and unavailable browsers keep typing usable", async ({
  page,
}) => {
  await mockApi(page);
  await mockSpeech(page);
  await page.goto("/new");
  const composer = page.getByRole("textbox", { name: "Nachricht", exact: true });
  await composer.fill("Mein Entwurf");
  await page.getByRole("button", { name: "Diktieren", exact: true }).click();
  await page.evaluate(() =>
    (window as SpeechTestWindow).speechInstances.at(-1)!.onerror?.({ error: "not-allowed" }),
  );
  await expect(page.getByRole("alert")).toContainText("Mikrofonzugriff");
  await expect(composer).toHaveValue("Mein Entwurf");
  await mockSpeech(page, false);
  await page.reload();
  await expect(
    page.getByRole("button", { name: "Diktieren wird von diesem Browser nicht unterstützt" }),
  ).toBeDisabled();
  await expect(composer).toBeEditable();
});

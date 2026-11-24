import { test, expect } from "@playwright/test";
import { mockApi, session } from "./fixtures";

test("protected route shows real login and retries a failed session", async ({ page }) => {
  await mockApi(page, false);
  await page.goto("/chat/deck-1");
  await expect(page.getByRole("button", { name: "Mit Spotify fortfahren" })).toBeVisible();
  await expect(page.locator("chat-page")).toHaveCount(0);
});
test("welcome, new session and generated RPC streaming", async ({ page }) => {
  const fixture = await mockApi(page);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/new");
  await expect(
    page.getByRole("heading", { name: "Jeder Hit hat seine Zeit. Welche ist deine?" }),
  ).toBeVisible();
  const model = page.getByRole("combobox", { name: "KI-Modell" });
  await expect(model).toHaveValue("gpt-6-luna-US");
  await expect(model).toHaveAttribute("title", "GPT 6 Luna (OpenAI)");
  await expect(page.getByRole("img", { name: "OpenAI", exact: true })).toBeVisible();
  await model.selectOption("gpt-6-sol-US");
  await expect(model).toHaveAttribute("title", "GPT 6 Sol (OpenAI)");
  await page.screenshot({ path: "test-results/studio-desktop.png", fullPage: true });
  await page.getByRole("button", { name: /Zurück in die 90er/ }).click();
  await expect(page.getByRole("textbox", { name: "Nachricht", exact: true })).toHaveValue(/90er/);
  await page.getByRole("button", { name: "Nachricht senden", exact: true }).click();
  await expect(page).toHaveURL(/\/chat\/new-deck/);
  await expect(page.locator("assistant-message")).toContainText("Hier ist dein Kartendeck.");
  await expect(page.locator("deck-panel")).toContainText("Dancing Queen");
  await expect(page.getByRole("textbox", { name: "Nachricht", exact: true })).toHaveValue("");
  expect(fixture.messages).toHaveLength(1);
  expect(fixture.modelIds).toEqual(["gpt-6-sol-US"]);
  await expect(model).toHaveValue("gpt-6-sol-US");
});

test("model selection stays distinct for Codex and survives mobile settings and locale changes", async ({
  page,
}) => {
  const fixture = await mockApi(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/new");
  const model = page.getByRole("combobox", { name: "KI-Modell" });
  await model.selectOption("gpt-6-sol-codex");
  await expect(model).toHaveAttribute("title", "GPT 6 Sol (Codex)");
  await expect(page.getByRole("img", { name: "OpenAI", exact: true })).toHaveAttribute(
    "title",
    "Codex",
  );
  const send = await page
    .getByRole("button", { name: "Nachricht senden", exact: true })
    .boundingBox();
  const selector = await model.boundingBox();
  expect(selector!.x + selector!.width).toBeLessThan(send!.x);
  await page.getByRole("button", { name: "Seitenleiste öffnen" }).click();
  await page.getByRole("button", { name: /Mathi · Konto und Einstellungen/ }).click();
  await page.getByRole("combobox", { name: "Sprache" }).selectOption("en");
  await page.getByRole("button", { name: "Open sidebar" }).click();
  await page.getByRole("button", { name: /New deck/ }).click();
  const englishModel = page.getByRole("combobox", { name: "AI model" });
  await expect(englishModel).toHaveValue("gpt-6-sol-codex");
  await expect(englishModel).toHaveAttribute("title", "GPT 6 Sol (Codex)");
  await page.getByRole("textbox", { name: "Message", exact: true }).fill("Disco for game night");
  await page.getByRole("button", { name: "Send message", exact: true }).click();
  await expect(page).toHaveURL(/\/chat\/new-deck/);
  await expect(page.getByRole("textbox", { name: "Message", exact: true })).toHaveValue("");
  expect(fixture.modelIds).toEqual(["gpt-6-sol-codex"]);
});
test("session, cards, binary PDF and Spotify export", async ({ page }) => {
  await mockApi(page);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/chat/deck-1");
  await expect(page.locator("deck-panel")).toContainText("Dancing Queen");
  await page.getByRole("tab", { name: "Karten", exact: true }).click();
  await expect(page.locator("deck-panel music-card")).toContainText("1976");
  await page.getByRole("checkbox", { name: "Auflösung verbergen" }).check();
  await expect(page.locator("deck-panel music-card")).not.toContainText("1976");
  await page.getByRole("tab", { name: "Export", exact: true }).click();
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "PDF herunterladen" }).click();
  expect((await download).suggestedFilename()).toBe("prompster-deck-1.pdf");
  await page.getByRole("button", { name: "Nach Spotify exportieren" }).click();
  await expect(page.getByRole("link", { name: "In Spotify öffnen" })).toHaveAttribute(
    "href",
    "https://open.spotify.com/playlist/spotify-deck",
  );
  await page.screenshot({ path: "test-results/deck-desktop.png", fullPage: true });
});
test("rename and star propagate to the collection", async ({ page }) => {
  await mockApi(page);
  await page.goto("/new");
  await page.getByRole("button", { name: "Aktionen für Unser Spieleabend" }).click();
  await page.getByRole("textbox", { name: "Deckname" }).fill("90er Party");
  await page.getByRole("button", { name: "Speichern", exact: true }).click();
  await expect(page.getByRole("button", { name: "90er Party", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Aktionen für 90er Party" }).click();
  await page.getByRole("button", { name: "Als Favorit speichern" }).click();
  await expect(page.getByRole("button", { name: /^Favoriten/ })).toBeVisible();
  await page.getByRole("button", { name: "Meine Decks", exact: true }).click();
  await expect(page.locator("library-page")).toContainText("90er Party");
});
test("mobile sidebar, composer and workspace stay usable", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await mockApi(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/new");
  await expect(page.getByRole("textbox", { name: "Nachricht", exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: "test-results/studio-mobile.png", fullPage: true });
  await page.getByRole("button", { name: "Seitenleiste öffnen" }).click();
  await page.getByRole("button", { name: "Unser Spieleabend", exact: true }).click();
  await page.getByRole("button", { name: "Deck öffnen" }).click();
  await expect(page.locator("deck-panel")).toBeVisible();
  await page.getByRole("button", { name: "Deck schließen", exact: true }).click();
  await expect(page.getByRole("textbox", { name: "Nachricht", exact: true })).toBeVisible();
  expect(errors).toEqual([]);
});

test("onboarding answers are persisted before the completion stream", async ({ page }) => {
  await mockApi(page);
  const draft = {
    ...session(),
    phase: "onboarding",
    onboardingQuestions: [
      {
        id: "question",
        sequenceNumber: 1,
        questionText: "Welche Jahrzehnte?",
        options: ["70er", "90er"],
        selectionMode: "multi_select",
        isLastQuestion: true,
        answers: [],
        isAnswered: false,
      },
    ],
  };
  let submitted: unknown;
  await page.route("**/api/v1/sessions/deck-1", (route) => route.fulfill({ json: draft }));
  await page.route("**/api/v1/sessions/deck-1/onboarding-answer", (route) => {
    submitted = route.request().postDataJSON();
    draft.phase = "curation";
    return route.fulfill({ json: draft });
  });
  await page.goto("/chat/deck-1");
  await page.getByRole("checkbox", { name: "70er", exact: true }).check();
  await page.getByRole("checkbox", { name: "90er", exact: true }).check();
  await page.getByRole("button", { name: "Deck zusammenstellen" }).click();
  await expect(page.locator("onboarding-panel")).toHaveCount(0);
  expect(submitted).toEqual({
    questionId: "question",
    answer: "70er, 90er",
    answers: ["70er", "90er"],
  });
});

test("stopping a live stream calls the backend and releases the composer", async ({ page }) => {
  await mockApi(page, true, true);
  await page.goto("/chat/deck-1");
  await page.getByRole("textbox", { name: "Nachricht", exact: true }).fill("Noch mehr Disco");
  await page.getByRole("button", { name: "Nachricht senden", exact: true }).click();
  await expect(page.getByRole("button", { name: "Antwort stoppen" })).toBeVisible();
  const stopRequest = page.waitForRequest(
    (request) => request.url().endsWith("/messages/stop") && request.method() === "POST",
  );
  await page.getByRole("button", { name: "Antwort stoppen" }).click();
  await stopRequest;
  await expect(page.getByRole("button", { name: "Nachricht senden", exact: true })).toBeVisible();
  await expect(page.getByRole("textbox", { name: "Nachricht", exact: true })).toBeEnabled();
});

test("switching sessions aborts the previous stream without leaking its state", async ({
  page,
}) => {
  await mockApi(page, true, true);
  await page.goto("/chat/deck-1");
  await page.getByRole("textbox", { name: "Nachricht", exact: true }).fill("Noch mehr Disco");
  await page.getByRole("button", { name: "Nachricht senden", exact: true }).click();
  await expect(page.getByRole("button", { name: "Antwort stoppen" })).toBeVisible();
  await page
    .getByRole("button", { name: /Neues Deck/ })
    .first()
    .click();
  await expect(page).toHaveURL(/\/new$/);
  await expect(page.locator("studio-page")).toBeVisible();
  await expect(page.getByRole("textbox", { name: "Nachricht", exact: true })).toHaveValue("");
  await expect(page.locator("assistant-message")).toHaveCount(0);
});

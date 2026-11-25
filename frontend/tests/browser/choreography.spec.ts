import { test, expect } from "@playwright/test";
import { deckBuildRun, mockAgentRun } from "./agent-run-fixture";
import { mockApi } from "./fixtures";

const send = async (page: import("@playwright/test").Page) => {
  await page.getByRole("textbox", { name: "Nachricht", exact: true }).fill("Ein 80er-Deck");
  await page.getByRole("button", { name: "Nachricht senden", exact: true }).click();
};
const titles = deckBuildRun.tracks.map((track) => track.title);

test("the agent's searches and deck edits play in the workspace", async ({ page }) => {
  await mockApi(page);
  await mockAgentRun(page, deckBuildRun, 6);
  await page.setViewportSize({ width: 1440, height: 960 });
  await page.goto("/chat/deck-1");
  const panel = page.locator("deck-panel");
  const stage = panel.locator(".agent-stage");
  await expect(panel).toContainText("Noch ist die Bühne leer.");
  await send(page);

  await expect(stage).toHaveAttribute("data-open", "");
  await expect(stage).toHaveAttribute("aria-hidden", "true");
  await expect(panel.locator("agent-search .query")).toHaveText("synthpop 1983");
  await expect(panel.locator("agent-search .hits.open .hit").first()).toContainText("Sweet Dreams");
  await expect(panel.getByRole("button", { name: "Songs hinzufügen" })).toBeDisabled();
  await expect(panel.locator("agent-search .hit.picked").first()).toBeVisible();
  await expect(panel.locator(".track").first()).toContainText("Sweet Dreams");

  await expect(stage).not.toHaveAttribute("data-open", "", { timeout: 30_000 });
  await expect(panel.locator(".track strong")).toHaveText(titles);
  await expect(panel.getByRole("button", { name: "Songs hinzufügen" })).toBeEnabled();
});

test("the chat lists the agent's tool calls and opens what a search found", async ({ page }) => {
  await mockApi(page);
  await mockAgentRun(page, deckBuildRun, 20);
  await page.goto("/chat/deck-1");
  await send(page);

  const research = page.locator("tool-call-chain").first();
  await expect(research).toContainText("Grabe in den 80ern");
  await expect(research.locator("li", { hasText: "new wave essentials" })).toContainText("4");
  await expect(page.locator("tool-call-chain").nth(1)).toContainText("Baue das 80er-Deck");
  await expect(page.locator("assistant-message").last()).toContainText("80er-Deck");

  const search = research.locator("details", { hasText: "Suche Tracks: synthpop 1983" });
  await expect(search.locator(".found")).toBeHidden();
  await search.locator("summary").click();
  await expect(search.locator(".found li")).toHaveCount(6);
  await expect(search.locator(".found li").first()).toHaveText(
    "Sweet Dreams (Are Made of This) · Eurythmics",
  );
});

test("with reduced motion the deck changes without the agent's search field", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await mockApi(page);
  await mockAgentRun(page, deckBuildRun, 20);
  await page.goto("/chat/deck-1");
  const panel = page.locator("deck-panel");
  await send(page);

  await expect(panel.locator(".track strong")).toHaveText(titles);
  await expect(panel.locator(".agent-stage")).not.toHaveAttribute("data-open", "");
  await expect(panel.locator("agent-search .field")).toHaveCount(0);
});

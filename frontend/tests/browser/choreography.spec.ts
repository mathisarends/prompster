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
  await expect(panel.locator("agent-search .hit").first()).toContainText("Sweet Dreams");
  await expect(panel.getByRole("button", { name: "Songs hinzufügen" })).toBeDisabled();
  await expect(panel.locator(".track").first()).toContainText("Sweet Dreams");
  await expect(panel.locator("agent-search .hit.picked").first()).toBeVisible();

  await expect(stage).not.toHaveAttribute("data-open", "", { timeout: 30_000 });
  await expect(panel.locator(".track strong")).toHaveText(titles);
  await expect(panel.getByRole("button", { name: "Songs hinzufügen" })).toBeEnabled();
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

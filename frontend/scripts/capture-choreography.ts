import { chromium, expect } from "@playwright/test";
import { mkdir, rename } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { deckBuildRun, mockAgentRun } from "../tests/browser/agent-run-fixture";
import { mockApi } from "../tests/browser/fixtures";

// Records the agent building and refining a deck, for reviewing the choreography.
const raw = fileURLToPath(new URL("../test-results/choreography/", import.meta.url));
await mkdir(raw, { recursive: true });
const baseURL = process.env.REVIEW_BASE_URL ?? "http://127.0.0.1:5175";
const size = { width: 1440, height: 900 };
const browser = await chromium.launch({
  channel: process.platform === "win32" ? "chrome" : undefined,
});
try {
  const context = await browser.newContext({
    viewport: size,
    locale: "de-DE",
    recordVideo: { dir: raw, size },
  });
  const page = await context.newPage();
  const failures: string[] = [];
  page.on("pageerror", (error) => failures.push(error.message));
  await mockApi(page);
  await mockAgentRun(page, deckBuildRun);
  await page.goto(`${baseURL}/chat/deck-1`);
  const panel = page.locator("deck-panel");
  await expect(panel).toContainText("Noch ist die Bühne leer.");
  await page.waitForTimeout(800);
  await page
    .getByRole("textbox", { name: "Nachricht", exact: true })
    .pressSequentially("Ein 80er-Deck zwischen Synthpop und New Wave, bitte.", { delay: 18 });
  await page.getByRole("button", { name: "Nachricht senden", exact: true }).click();
  await expect(page.locator("assistant-message").last()).toContainText("80er-Deck", {
    timeout: 60_000,
  });
  await expect(panel.locator(".agent-stage")).not.toHaveAttribute("data-open", "", {
    timeout: 20_000,
  });
  await page.waitForTimeout(1200);
  await page.locator("tool-call-chain summary").first().click();
  await page.waitForTimeout(2200);
  const video = page.video()!;
  await context.close();
  await rename(await video.path(), `${raw}deck-build.webm`);
  if (failures.length) {
    throw new Error(failures.join("\n"));
  }
  process.stdout.write(`Recorded ${raw}deck-build.webm\n`);
} finally {
  await browser.close();
}

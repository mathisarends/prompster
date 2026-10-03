import { test, expect, type Page } from "@playwright/test";

const song = {
  id: "track-1",
  title: "Dancing Queen",
  artist: "ABBA",
  year: 1976,
  spotifyUri: "spotify:track:track-1",
  coverUrl: null,
};
const user = {
  id: "user",
  name: "Mathi",
  createdAt: "2026-01-01T00:00:00Z",
  spotifyConnected: true,
  spotifyPremium: false,
};
function session(id = "deck-1") {
  return {
    id,
    title: "Unser Spieleabend",
    isStarred: false,
    phase: "curation",
    createdAt: "2026-10-01T12:00:00Z",
    entries: [
      {
        id: "human",
        kind: "user_message",
        content: "Ein Deck voller Klassiker",
        createdAt: "2026-10-01T12:00:00Z",
      },
      {
        id: "answer",
        kind: "assistant_message",
        content: "Hier ist dein **Kartendeck**.",
        createdAt: "2026-10-01T12:00:01Z",
      },
    ],
    playlist: { id: "playlist", name: "Game Night", tracks: [song] },
    onboardingQuestions: [],
    unconsumedUserCurationEvents: [],
  };
}

async function mockApi(page: Page, authenticated = true, slow = false) {
  let current = session();
  let removed = false;
  const messages: string[] = [];
  await page.route("**/api/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    const method = route.request().method();
    const json = (value: unknown, status = 200) => route.fulfill({ status, json: value });
    if (path === "/api/v1/users/me") {
      return authenticated
        ? json(user)
        : json({ type: "about:blank", title: "Authentication required", status: 401 }, 401);
    }
    if (path === "/api/v1/auth/refresh") {
      return json({}, 401);
    }
    if (path === "/api/v1/llm-options") {
      return json({ items: [{ id: "default", label: "Standard", isDefault: true }] });
    }
    if (path === "/api/v1/sessions") {
      if (method === "POST") {
        current = {
          ...session("new-deck"),
          title: "",
          entries: [],
          playlist: null,
        } as unknown as ReturnType<typeof session>;
        return json(current, 201);
      }
      return json({
        items: removed
          ? []
          : [
              {
                id: current.id,
                title: current.title,
                isStarred: current.isStarred,
                createdAt: current.createdAt,
                lastActivityAt: current.createdAt,
              },
            ],
      });
    }
    if (path.endsWith("/playlist/pdf")) {
      return route.fulfill({ contentType: "application/pdf", body: "%PDF-1.4\n%%EOF" });
    }
    if (path.endsWith("/messages/stop")) {
      return route.fulfill({ status: 204 });
    }
    if (path.endsWith("/star")) {
      current.isStarred = true;
      return json(current);
    }
    if (path.endsWith("/unstar")) {
      current.isStarred = false;
      return json(current);
    }
    if (path.includes("/tracks/track-1") && method === "DELETE") {
      current.playlist.tracks = [];
      return route.fulfill({ status: 204 });
    }
    if (/\/sessions\/[^/]+$/.test(path)) {
      if (method === "PATCH") {
        current.title = route.request().postDataJSON().title;
      }
      if (method === "DELETE") {
        removed = true;
        return route.fulfill({ status: 204 });
      }
      return json(current);
    }
    if (path === "/api/v1/spotify/search") {
      return json({ tracks: [song], playlists: [], artists: [] });
    }
    return json({ detail: `Unhandled fixture: ${method} ${path}` }, 404);
  });
  await page.routeWebSocket(/\/api\/v1\/sessions\/.*\/stream/, (socket) => {
    socket.onMessage((raw) => {
      const request = JSON.parse(String(raw));
      if (request.method.endsWith(".unsubscribe")) {
        socket.send(JSON.stringify({ jsonrpc: "2.0", id: request.id, result: null }));
        return;
      }
      if (!request.method.endsWith(".subscribe")) {
        return;
      }
      const method = request.method.replace(/\.subscribe$/, "");
      socket.send(
        JSON.stringify({
          jsonrpc: "2.0",
          id: request.id,
          result: { subscriptionId: "subscription" },
        }),
      );
      const send = (payload: unknown) =>
        socket.send(
          JSON.stringify({
            jsonrpc: "2.0",
            method,
            params: { subscriptionId: "subscription", payload },
          }),
        );
      if (slow) {
        send({
          type: "message.assistant_started",
          messageId: "reply",
          createdAt: current.createdAt,
        });
        send({ type: "message.assistant_chunk", messageId: "reply", chunk: "Recherche läuft …" });
        return;
      }
      if (method === "session.export_spotify") {
        send({ type: "spotify_export.retry", attempt: 2, maxAttempts: 3 });
        send({
          type: "spotify_export.completed",
          playlist: {
            id: "spotify-deck",
            name: "Game Night",
            url: "https://open.spotify.com/playlist/spotify-deck",
            trackCount: 1,
            description: "",
          },
        });
      } else {
        messages.push(request.params.content);
        current = session(current.id);
        send({ type: "session.title_generated", title: current.title });
        send({
          type: "message.assistant_started",
          messageId: "reply",
          createdAt: current.createdAt,
        });
        send({
          type: "message.assistant_chunk",
          messageId: "reply",
          chunk: "Hier ist dein **Kartendeck**.",
        });
        send({ type: "playlist.set", playlist: current.playlist });
      }
      send({ type: "done" });
      socket.send(
        JSON.stringify({
          jsonrpc: "2.0",
          method,
          params: { subscriptionId: "subscription", complete: true },
        }),
      );
    });
  });
  return { messages };
}

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
  await page.screenshot({ path: "test-results/studio-desktop.png", fullPage: true });
  await page.getByRole("button", { name: /Zurück in die 90er/ }).click();
  await expect(page.getByRole("textbox", { name: "Nachricht", exact: true })).toHaveValue(/90er/);
  await page.getByRole("button", { name: "Nachricht senden", exact: true }).click();
  await expect(page).toHaveURL(/\/chat\/new-deck/);
  await expect(page.locator("assistant-message")).toContainText("Hier ist dein Kartendeck.");
  await expect(page.locator("deck-panel")).toContainText("Dancing Queen");
  await expect(page.getByRole("textbox", { name: "Nachricht", exact: true })).toHaveValue("");
  expect(fixture.messages).toHaveLength(1);
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
  await expect(page.getByText("FAVORITEN", { exact: true })).toBeVisible();
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
  await page.getByRole("button", { name: /Dein Deck/ }).click();
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

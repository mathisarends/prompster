import type { Page } from "@playwright/test";
import type { LLMOptionResponse } from "../../src/api/generated/llm-options";

// Representative entries from the backend registry, including its actual default.
export const modelOptions = (
  [
    {
      id: "gpt-6-sol-US",
      provider: "openai",
      label: "GPT 6 Sol (OpenAI)",
      profile: "Maximal",
      isDefault: false,
    },
    {
      id: "gpt-6-luna-US",
      provider: "openai",
      label: "GPT 6 Luna (OpenAI)",
      profile: "Schnell",
      isDefault: true,
    },
    {
      id: "gpt-6-sol-codex",
      provider: "codex",
      label: "GPT 6 Sol (Codex)",
      profile: "Maximal",
      isDefault: false,
    },
  ] as const
).map<LLMOptionResponse>((model) => ({
  ...model,
  capabilities: { temperature: false, reasoningEffort: ["low", "medium", "high"] },
  defaults: { reasoningEffort: "medium" },
}));

export const song = {
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
export function session(id = "deck-1") {
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

/** Frames events the way fastapi-canon streams them, ending with its completion event. */
const sseBody = (events: unknown[]): string =>
  events.map((event) => `data: ${JSON.stringify(event)}\n\n`).join("") +
  "event: canon.complete\ndata: {}\n\n";

export async function mockApi(
  page: Page,
  authenticated = true,
  slow = false,
  initialSession = session(),
) {
  let current = structuredClone(initialSession);
  let removed = false;
  const messages: string[] = [];
  const modelIds: (string | undefined)[] = [];
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
      return json({ items: modelOptions });
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
                // Mirrors the backend: up to four distinct covers in playlist order.
                coverUrls: [
                  ...new Set(
                    (current.playlist?.tracks ?? []).flatMap((track) =>
                      track.coverUrl ? [track.coverUrl] : [],
                    ),
                  ),
                ].slice(0, 4),
              },
            ],
      });
    }
    if (
      method === "POST" &&
      /\/(messages|onboarding\/complete|playlist\/spotify-export)$/.test(path)
    ) {
      // An open stream that never finishes, so the UI stays busy.
      if (slow) {
        return new Promise<void>(() => {});
      }
      const events: unknown[] = [];
      if (path.endsWith("/playlist/spotify-export")) {
        events.push(
          { type: "spotify_export.retry", attempt: 2, maxAttempts: 3 },
          {
            type: "spotify_export.completed",
            playlist: {
              id: "spotify-deck",
              name: "Game Night",
              url: "https://open.spotify.com/playlist/spotify-deck",
              trackCount: 1,
              description: "",
            },
          },
        );
      } else {
        const body = route.request().postDataJSON();
        messages.push(body.content);
        modelIds.push(body.modelId);
        current = { ...structuredClone(initialSession), id: current.id };
        events.push(
          { type: "session.title_generated", title: current.title },
          { type: "message.assistant_started", messageId: "reply", createdAt: current.createdAt },
          {
            type: "message.assistant_chunk",
            messageId: "reply",
            chunk: "Hier ist dein **Kartendeck**.",
          },
          { type: "playlist.set", playlist: current.playlist },
        );
      }
      events.push({ type: "done" });
      return route.fulfill({ contentType: "text/event-stream", body: sseBody(events) });
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
  return { messages, modelIds };
}

import type { Page } from "@playwright/test";

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

export async function mockApi(
  page: Page,
  authenticated = true,
  slow = false,
  initialSession = session(),
) {
  let current = structuredClone(initialSession);
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
        current = { ...structuredClone(initialSession), id: current.id };
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

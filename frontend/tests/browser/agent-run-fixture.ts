import type { Page } from "@playwright/test";
import type { SessionStreamEvent } from "../../src/api/session-streams";
import { session, song } from "./fixtures";

type Track = typeof song;
type Timed = { at: number; event: SessionStreamEvent };
/** A turn's events at their offsets in milliseconds, and the deck and reply it ends with. */
export type AgentRun = { timeline: Timed[]; tracks: Track[]; reply: string };

/** A flat two-tone cover, so recordings need no artwork from the network. */
const cover = (seed: number): string =>
  `data:image/svg+xml,${encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 8 8"><rect width="8" height="8" fill="hsl(${(seed * 47) % 360} 55% 42%)"/><circle cx="6" cy="6" r="4" fill="hsl(${(seed * 47 + 140) % 360} 60% 62%)"/></svg>`,
  )}`;

const catalog = (
  [
    ["Sweet Dreams (Are Made of This)", "Eurythmics", 1983],
    ["Blue Monday", "New Order", 1983],
    ["Just Can't Get Enough", "Depeche Mode", 1981],
    ["Tainted Love", "Soft Cell", 1981],
    ["Take On Me", "a-ha", 1985],
    ["Don't You Want Me", "The Human League", 1981],
    ["Just Like Heaven", "The Cure", 1987],
    ["Once in a Lifetime", "Talking Heads", 1980],
    ["Come On Eileen", "Dexys Midnight Runners", 1982],
    ["99 Luftballons", "Nena", 1983],
    ["Video Killed the Radio Star", "The Buggles", 1979],
    ["Major Tom (Völlig losgelöst)", "Peter Schilling", 1982],
  ] as const
).map(([title, artist, year], index): Track => ({
  id: `track-${index}`,
  title,
  artist,
  year,
  spotifyUri: `spotify:track:${index}`,
  coverUrl: cover(index),
}));
const [sweetDreams, blueMonday, enough, taintedLove, takeOnMe, humanLeague, heaven, lifetime] =
  catalog;
const [, , , , , , , , eileen, luftballons, buggles, majorTom] = catalog;

const hits = (tracks: Track[]) =>
  tracks.map((track) => ({
    title: track.title,
    artist: track.artist,
    coverUrl: track.coverUrl,
    trackUri: track.spotifyUri,
  }));

type Call = {
  id: string;
  state: "pending" | "completed";
  function: {
    name: string;
    arguments: Record<string, string>;
    statusLabel: string;
    actionType: string;
  };
};
const call = (
  id: string,
  name: string,
  args: Record<string, string>,
  statusLabel: string,
): Call => ({
  id,
  state: "pending",
  function: { name, arguments: args, statusLabel, actionType: name },
});
const search = (id: string, query: string) =>
  call(id, "search_tracks", { query }, `Suche Tracks: ${query}`);
const sequence = (id: string, label: string, calls: Call[]): SessionStreamEvent => ({
  type: "tool_call.sequence_added",
  sequence: { id, label, createdAt: "2026-10-01T12:00:02Z", calls },
});
const resolved = (
  sequenceId: string,
  toolCallId: string,
  found: Track[] = [],
): SessionStreamEvent => ({
  type: "tool_call.resolved",
  sequenceId,
  toolCallId,
  result: "ok",
  resultItems: hits(found),
});

const built = [sweetDreams, takeOnMe, blueMonday, eileen, taintedLove, luftballons, heaven, enough];
const final = [taintedLove, eileen, majorTom, sweetDreams, blueMonday, luftballons, takeOnMe];
const refine = "Schärfe das Deck nach";
const swap = call("r1", "replace_deck_tracks", {}, "Tausche einen Song für mehr Überraschung");

const reply =
  "Dein **80er-Deck** steht: Synthpop, New Wave und zwei One-Hit-Wonder, nach Jahren sortiert.";

/**
 * One agent turn on an empty deck, timed like a real one: three searches, a
 * deck of eight tracks, then a swap, a removal and a new order.
 */
export const deckBuildRun: AgentRun = {
  tracks: final,
  reply,
  timeline: [
    {
      at: 0,
      event: { type: "session.title_generated", title: "80er zwischen Synthpop und New Wave" },
    },
    {
      at: 300,
      event: sequence("research", "Grabe in den 80ern", [search("s1", "synthpop 1983")]),
    },
    {
      at: 340,
      event: sequence("research", "Grabe in den 80ern", [
        search("s1", "synthpop 1983"),
        search("s2", "new wave essentials"),
        search("s3", "one hit wonder 80s"),
      ]),
    },
    {
      at: 1200,
      event: resolved("research", "s1", [
        sweetDreams,
        blueMonday,
        enough,
        taintedLove,
        takeOnMe,
        humanLeague,
      ]),
    },
    { at: 1500, event: resolved("research", "s2", [heaven, lifetime, blueMonday, humanLeague]) },
    {
      at: 1800,
      event: resolved("research", "s3", [eileen, luftballons, buggles, majorTom, taintedLove]),
    },
    { at: 1900, event: { type: "tool_call.sequence_completed", sequenceId: "research" } },
    {
      at: 6600,
      event: sequence("build", "Baue das 80er-Deck", [
        call("a1", "add_deck_tracks", {}, "Baue das 80er-Deck"),
      ]),
    },
    {
      at: 7000,
      event: { type: "playlist.set", playlist: { id: "playlist", name: "80er", tracks: built } },
    },
    { at: 7050, event: resolved("build", "a1") },
    { at: 7100, event: { type: "tool_call.sequence_completed", sequenceId: "build" } },
    { at: 14500, event: sequence("refine", refine, [swap]) },
    {
      at: 14900,
      event: {
        type: "playlist.track_replaced",
        playlistId: "playlist",
        trackId: heaven.id,
        track: majorTom,
      },
    },
    { at: 14950, event: resolved("refine", "r1") },
    {
      at: 17600,
      event: sequence("refine", refine, [
        { ...swap, state: "completed" },
        call("r2", "remove_deck_tracks", {}, "Nehme einen Song heraus"),
      ]),
    },
    {
      at: 18000,
      event: { type: "playlist.track_removed", playlistId: "playlist", trackId: enough.id },
    },
    { at: 18050, event: resolved("refine", "r2") },
    { at: 18100, event: { type: "tool_call.sequence_completed", sequenceId: "refine" } },
    {
      at: 20500,
      event: { type: "playlist.set", playlist: { id: "playlist", name: "80er", tracks: final } },
    },
    {
      at: 23500,
      event: {
        type: "message.assistant_started",
        messageId: "reply",
        createdAt: "2026-10-01T12:00:20Z",
      },
    },
    {
      at: 23600,
      event: {
        type: "message.assistant_chunk",
        messageId: "reply",
        chunk: reply,
      },
    },
    { at: 24200, event: { type: "done" } },
  ],
};

/**
 * Answers the page's message stream with `run`, each event at its offset, and
 * serves the session as the turn leaves it once the stream opened. Call it
 * after `mockApi`. `speed` above 1 plays the run faster.
 */
export async function mockAgentRun(page: Page, run: AgentRun, speed = 1): Promise<void> {
  const frames = run.timeline.map(({ at, event }) => ({
    at: at / speed,
    frame: `data: ${JSON.stringify(event)}\n\n`,
  }));
  frames.push({
    at: (frames.at(-1)?.at ?? 0) + 20,
    frame: "event: canon.complete\ndata: {}\n\n",
  });
  let message: string | undefined;
  await page.exposeFunction("agentRunStarted", (content: string) => {
    message = content;
  });
  // A route can only answer in one piece, so the page streams the frames itself.
  await page.addInitScript((timed) => {
    const original = window.fetch;
    window.fetch = (input, init) => {
      const url = new URL(input instanceof Request ? input.url : String(input), location.href);
      if (init?.method !== "POST" || !url.pathname.endsWith("/messages")) {
        return original(input, init);
      }
      const started = (window as unknown as { agentRunStarted(content: string): Promise<void> })
        .agentRunStarted;
      void started(JSON.parse(String(init.body)).content);
      const encoder = new TextEncoder();
      const timers: number[] = [];
      const body = new ReadableStream<Uint8Array>({
        start(controller) {
          timed.forEach(({ at, frame }, index) =>
            timers.push(
              window.setTimeout(() => {
                controller.enqueue(encoder.encode(frame));
                if (index === timed.length - 1) {
                  controller.close();
                }
              }, at),
            ),
          );
        },
        cancel() {
          timers.forEach((timer) => window.clearTimeout(timer));
        },
      });
      return Promise.resolve(
        new Response(body, { headers: { "content-type": "text/event-stream" } }),
      );
    };
  }, frames);
  await page.route(/\/api\/v1\/sessions\/[^/]+$/, (route) => {
    if (route.request().method() !== "GET") {
      return route.fallback();
    }
    const base = session(new URL(route.request().url()).pathname.split("/").pop());
    const createdAt = base.createdAt;
    const sequences = new Map<string, unknown>();
    for (const { event } of run.timeline) {
      if (event.type === "tool_call.sequence_added") {
        sequences.set(event.sequence.id, {
          ...event.sequence,
          kind: "tool_call_sequence",
          calls: event.sequence.calls.map((item) => ({ ...item, state: "completed" })),
        });
      }
    }
    return route.fulfill({
      json: {
        ...base,
        title: message === undefined ? "Neues Deck" : "80er zwischen Synthpop und New Wave",
        entries:
          message === undefined
            ? []
            : [
                { id: "human", kind: "user_message", content: message, createdAt },
                ...sequences.values(),
                { id: "reply", kind: "assistant_message", content: run.reply, createdAt },
              ],
        playlist: { id: "playlist", name: "80er", tracks: message === undefined ? [] : run.tracks },
      },
    });
  });
}

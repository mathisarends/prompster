import type { Page } from "@playwright/test";
import type { SessionStreamEvent } from "../../src/api/session-streams";
import { session, song } from "./fixtures";

type Track = typeof song;
type Timed = { at: number; event: SessionStreamEvent };
/**
 * A turn's events at their offsets in milliseconds, with what the agent says
 * before it starts, and the deck and reply the turn ends with.
 */
export type AgentRun = { timeline: Timed[]; tracks: Track[]; opening: string; reply: string };

/** Title, artist, year and the path of the album artwork. */
const songs = [
  [
    "Sweet Dreams (Are Made of This)",
    "Eurythmics",
    1983,
    "Music124/v4/f2/4c/c2/f24cc223-f889-c8a3-ebbc-8ce458438580/mzi.zbvljpxb.jpg",
  ],
  [
    "Blue Monday",
    "New Order",
    1983,
    "Music124/v4/c4/c5/4c/c4c54c3d-5305-edad-dc50-5bb51c2bedca/190295421069.jpg",
  ],
  [
    "Just Can't Get Enough",
    "Depeche Mode",
    1981,
    "Music115/v4/19/b8/13/19b81309-d81c-66f7-25b5-ecf545bc2db7/0094635797954.jpg",
  ],
  [
    "Tainted Love",
    "Soft Cell",
    1981,
    "Music116/v4/bc/9f/41/bc9f4106-5f66-07ba-d577-904e492e5ac9/23UMGIM98408.rgb.jpg",
  ],
  [
    "Take On Me",
    "a-ha",
    1985,
    "Music115/v4/0b/5b/69/0b5b6991-cd46-7222-fca7-680b17318721/603497888191.jpg",
  ],
  [
    "Don't You Want Me",
    "The Human League",
    1981,
    "Music221/v4/a8/92/3b/a8923b58-1db6-6cca-81f7-3fcb575b5a40/13UABIM56815.rgb.jpg",
  ],
  [
    "Just Like Heaven",
    "The Cure",
    1987,
    "Music116/v4/bc/dd/f1/bcddf110-d7d2-0164-ba71-d8dd90e94599/06UMGIM44997.rgb.jpg",
  ],
  [
    "Once in a Lifetime",
    "Talking Heads",
    1980,
    "Music125/v4/48/9c/21/489c217b-d228-59a3-296d-6fa1d90776b7/dj.bpkztuma.jpg",
  ],
  [
    "Come On Eileen",
    "Dexys Midnight Runners",
    1982,
    "Music124/v4/98/a5/7c/98a57c6d-c857-90bb-5835-fdd60699bf05/06UMGIM09147.rgb.jpg",
  ],
  [
    "99 Luftballons",
    "Nena",
    1983,
    "Music128/v4/d8/a2/0b/d8a20b88-4fc1-5f7a-36f3-48bf6cf3519c/0859381160700.jpg",
  ],
  [
    "Video Killed the Radio Star",
    "The Buggles",
    1979,
    "Music115/v4/16/21/ea/1621eaf0-f7c8-c9e9-5eaf-e11a7ec87610/06UMGIM01037.rgb.jpg",
  ],
  [
    "Major Tom (Völlig losgelöst)",
    "Peter Schilling",
    1982,
    "Music125/v4/df/a8/e1/dfa8e123-28cd-b772-c172-1f14845cf959/190295013738.jpg",
  ],
] as const;

type Cover = (index: number) => string;
/** A flat two-tone cover, so tests need no artwork from the network. */
const flat: Cover = (seed) =>
  `data:image/svg+xml,${encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 8 8"><rect width="8" height="8" fill="hsl(${(seed * 47) % 360} 55% 42%)"/><circle cx="6" cy="6" r="4" fill="hsl(${(seed * 47 + 140) % 360} 60% 62%)"/></svg>`,
  )}`;
/** The song's album artwork, loaded from the network. */
const artwork: Cover = (index) =>
  `https://is1-ssl.mzstatic.com/image/thumb/${songs[index][3]}/300x300bb.jpg`;

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

const opening = "Alles klar, ich grabe mich mal durch die 80er.";
const reply =
  "Dein **80er-Deck** steht: Synthpop, New Wave und zwei One-Hit-Wonder, nach Jahren sortiert.";
const refine = "Schärfe das Deck nach";
const swap = call("r1", "replace_deck_tracks", {}, "Tausche einen Song für mehr Überraschung");

/**
 * One agent turn on an empty deck, timed like a real one: a word that it
 * starts, three searches, a deck of eight tracks, then a swap, a removal and a
 * new order.
 */
function deckBuild(cover: Cover): AgentRun {
  const catalog = songs.map(([title, artist, year], index): Track => ({
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
  const built = [
    sweetDreams,
    takeOnMe,
    blueMonday,
    eileen,
    taintedLove,
    luftballons,
    heaven,
    enough,
  ];
  const final = [taintedLove, eileen, majorTom, sweetDreams, blueMonday, luftballons, takeOnMe];
  return {
    tracks: final,
    opening,
    reply,
    timeline: [
      {
        at: 0,
        event: { type: "session.title_generated", title: "80er zwischen Synthpop und New Wave" },
      },
      {
        at: 150,
        event: {
          type: "message.assistant_started",
          messageId: "opening",
          createdAt: "2026-10-01T12:00:01Z",
        },
      },
      {
        at: 200,
        event: { type: "message.assistant_chunk", messageId: "opening", chunk: opening },
      },
      {
        at: 900,
        event: sequence("research", "Grabe in den 80ern", [search("s1", "synthpop 1983")]),
      },
      {
        at: 940,
        event: sequence("research", "Grabe in den 80ern", [
          search("s1", "synthpop 1983"),
          search("s2", "new wave essentials"),
          search("s3", "one hit wonder 80s"),
        ]),
      },
      {
        at: 1800,
        event: resolved("research", "s1", [
          sweetDreams,
          blueMonday,
          enough,
          taintedLove,
          takeOnMe,
          humanLeague,
        ]),
      },
      { at: 2100, event: resolved("research", "s2", [heaven, lifetime, blueMonday, humanLeague]) },
      {
        at: 2400,
        event: resolved("research", "s3", [eileen, luftballons, buggles, majorTom, taintedLove]),
      },
      { at: 2500, event: { type: "tool_call.sequence_completed", sequenceId: "research" } },
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
        event: { type: "message.assistant_chunk", messageId: "reply", chunk: reply },
      },
      { at: 24200, event: { type: "done" } },
    ],
  };
}

export const deckBuildRun = deckBuild(flat);
/** The same turn with album artwork from the network, for recordings. */
export const deckBuildRunWithArtwork = deckBuild(artwork);

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
    const found = new Map(
      run.timeline.flatMap(({ event }) =>
        event.type === "tool_call.resolved"
          ? [[event.toolCallId, event.resultItems ?? []] as const]
          : [],
      ),
    );
    const sequences = new Map<string, unknown>();
    for (const { event } of run.timeline) {
      if (event.type === "tool_call.sequence_added") {
        sequences.set(event.sequence.id, {
          ...event.sequence,
          kind: "tool_call_sequence",
          calls: event.sequence.calls.map((item) => ({
            ...item,
            state: "completed",
            resultItems: found.get(item.id) ?? [],
          })),
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
                { id: "opening", kind: "assistant_message", content: run.opening, createdAt },
                ...sequences.values(),
                { id: "reply", kind: "assistant_message", content: run.reply, createdAt },
              ],
        playlist: { id: "playlist", name: "80er", tracks: message === undefined ? [] : run.tracks },
      },
    });
  });
}

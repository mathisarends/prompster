import { test } from "node:test";
import assert from "node:assert/strict";
import type { SessionStreamEvent } from "../src/api/session-streams/index.ts";
import { CueScript, type StageTrack } from "../src/features/deck/choreography/cues.ts";
import { PlaylistChoreography } from "../src/features/deck/choreography/playlist-choreography.ts";
import type { Stage } from "../src/features/deck/choreography/stage.ts";
import { Feed } from "../src/shared/feed.ts";

const track = (name: string): StageTrack => ({
  id: name,
  title: `Song ${name}`,
  artist: "Artist",
  year: 1984,
  spotifyUri: `spotify:track:${name}`,
});
const searchCall = (id: string, query: string, state: "pending" | "completed" = "pending") => ({
  id,
  state,
  function: { name: "search_tracks", arguments: { query } },
});
const searching = (...calls: ReturnType<typeof searchCall>[]): SessionStreamEvent => ({
  type: "tool_call.sequence_added",
  sequence: { id: "sequence", createdAt: "2026-10-01T12:00:00Z", calls },
});
const found = (toolCallId: string, tracks: StageTrack[]): SessionStreamEvent => ({
  type: "tool_call.resolved",
  sequenceId: "sequence",
  toolCallId,
  result: "ok",
  resultItems: tracks.map(({ title, spotifyUri }) => ({ title, trackUri: spotifyUri })),
});
const deck = (tracks: StageTrack[]): SessionStreamEvent => ({
  type: "playlist.set",
  playlist: { id: "deck", tracks },
});
const added = (item: StageTrack): SessionStreamEvent => ({
  type: "playlist.track_added",
  playlistId: "deck",
  track: item,
});

/** A choreography on a clock that never waits, recording every stage it shows. */
function staging(base: StageTrack[] = [], reducedMotion = false) {
  const feed = new Feed<SessionStreamEvent>();
  const shown: Stage[] = [];
  let elapsed = 0;
  const choreography = new PlaylistChoreography(
    {
      addController: () => undefined,
      removeController: () => undefined,
      requestUpdate: () => {
        if (choreography.stage) {
          shown.push(choreography.stage);
        }
      },
      updateComplete: Promise.resolve(true),
    },
    {
      tracks: () => base,
      reducedMotion: () => reducedMotion,
      clock: {
        sleep: (ms) => {
          elapsed += ms;
          return Promise.resolve();
        },
      },
    },
  );
  choreography.follow(feed);
  choreography.setRunning(true);
  return {
    choreography,
    shown,
    elapsed: () => elapsed,
    async play(...events: SessionStreamEvent[]) {
      events.forEach((event) => feed.publish(event));
      await new Promise((resolve) => setTimeout(resolve));
    },
  };
}
const ids = (stage: Stage | undefined) => stage?.tracks.map((item) => item.id);

test("a search is typed, shows its hits and marks the track the deck takes", async () => {
  const [a, b] = [track("a"), track("b")];
  const { choreography, shown, play } = staging();
  await play(searching(searchCall("s1", "abba")), found("s1", [a, b]), deck([b]));

  const queries = shown.flatMap((stage) => (stage.search ? [stage.search.query] : []));
  assert.deepEqual([...new Set(queries)], ["", "a", "ab", "abb", "abba"]);
  const results = shown.find((stage) => stage.search?.status === "results");
  assert.deepEqual(
    results?.search?.hits.map((hit) => hit.key),
    [a.spotifyUri, b.spotifyUri],
  );
  assert.deepEqual(results?.tracks, []);
  assert.deepEqual(choreography.stage?.search?.picked, [b.spotifyUri]);
  assert.deepEqual(ids(choreography.stage!), ["b"]);
  assert.equal(choreography.stage?.marks.b, "added");
});

test("tracks are marked search by search before any lands, and the hits are gone by then", async () => {
  const [a, b, c] = ["a", "b", "c"].map(track);
  const { choreography, shown, play } = staging();
  await play(
    searching(searchCall("s1", "abba"), searchCall("s2", "queen")),
    found("s1", [a, b]),
    found("s2", [c]),
  );
  shown.length = 0;
  await play(added(a), added(c), added(b));

  const marks = shown.flatMap((stage) =>
    stage.search?.picked.length ? [`${stage.search.callId}:${stage.search.picked.at(-1)}`] : [],
  );
  assert.deepEqual(
    [...new Set(marks)],
    [`s1:${a.spotifyUri}`, `s1:${b.spotifyUri}`, `s2:${c.spotifyUri}`],
  );
  const landing = shown.filter((stage) => stage.tracks.length);
  assert.ok(landing.every((stage) => stage.search?.status === "idle"));
  assert.deepEqual(ids(choreography.stage!), ["a", "c", "b"]);
  assert.deepEqual(choreography.stage?.chosen, []);
});

test("a search sent again with its sequence is typed once", () => {
  const script = new CueScript();
  assert.equal(script.read(searching(searchCall("s1", "abba"))).length, 1);
  const cues = script.read(searching(searchCall("s1", "abba"), searchCall("s2", "queen")));
  assert.deepEqual(
    cues.map((cue) => cue.kind === "search" && cue.query),
    ["queen"],
  );
  assert.deepEqual(script.read(searching(searchCall("s3", "old", "completed"))), []);
});

test("a whole new deck plays as tracks leaving, landing and taking their order", async () => {
  const [a, b, c, d] = ["a", "b", "c", "d"].map(track);
  const { choreography, shown, play } = staging([a, b, c]);
  await play(deck([c, a, d]));

  const order = [...new Set(shown.map((stage) => ids(stage)!.join("")))];
  assert.deepEqual(order, ["abc", "ac", "acd", "cad"]);
  assert.equal(shown.find((stage) => ids(stage)!.join("") === "abc")?.marks.b, "leaving");
  assert.equal(choreography.stage?.marks.d, "added");
});

test("a replaced track is typed into its row", async () => {
  const [a, b, c] = ["a", "b", "c"].map(track);
  const { choreography, shown, play } = staging([a, b]);
  await play({ type: "playlist.track_replaced", playlistId: "deck", trackId: "b", track: c });

  const typed = shown.flatMap((stage) => (stage.rewrite ? [stage.rewrite.title] : []));
  assert.equal(typed[0], "");
  assert.equal(typed.at(-1), c.title);
  assert.deepEqual(ids(choreography.stage!), ["a", "c"]);
  assert.equal(choreography.stage?.rewrite, null);
});

test("the stage hands back to the deck once the turn ended and all was shown", async () => {
  const { choreography, shown, play } = staging();
  await play(searching(searchCall("s1", "abba")), added(track("a")));
  assert.ok(choreography.stage);

  choreography.setRunning(false);
  await play();
  assert.equal(choreography.stage, null);
  assert.equal(shown.at(-1)?.search, null);
});

test("an unanswered search does not hold up a turn that ended", async () => {
  const { choreography, play } = staging();
  await play(searching(searchCall("s1", "abba")));
  choreography.setRunning(false);
  await play();
  assert.equal(choreography.stage, null);
});

test("a backlog plays faster than the same cues one by one", async () => {
  const tracks = Array.from({ length: 20 }, (_, index) => track(`t${index}`));
  const single = staging();
  await single.play(added(tracks[0]));
  const burst = staging();
  await burst.play(...tracks.map(added));

  assert.deepEqual(
    ids(burst.choreography.stage!),
    tracks.map((item) => item.id),
  );
  assert.ok(burst.elapsed() < single.elapsed() * 10);
});

test("with reduced motion nothing is staged", async () => {
  const { choreography, play } = staging([], true);
  await play(searching(searchCall("s1", "abba")), deck([track("a")]));
  assert.equal(choreography.stage, null);
});

test("a new session forgets what was staged", async () => {
  const { choreography, play } = staging();
  await play(added(track("a")));
  choreography.reset();
  assert.equal(choreography.stage, null);
});

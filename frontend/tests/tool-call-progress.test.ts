import { test } from "node:test";
import assert from "node:assert/strict";
import type { ChatEntry } from "../src/features/chat/state/chat-reducer.ts";
import { followProgress } from "../src/features/chat/state/tool-call-progress.ts";

const message = (id: string) =>
  ({ id, kind: "assistant_message", content: id, createdAt: "" }) as ChatEntry;
const group = (id: string, ...calls: string[]) =>
  ({
    id,
    kind: "tool_call_group",
    createdAt: "",
    calls: calls.map((call) => ({
      id: call,
      state: "completed",
      function: { name: "search_tracks", arguments: {} },
      resultItems: [{ title: "Song" }],
    })),
  }) as ChatEntry;
const calls = (entry: ChatEntry) =>
  entry.kind === "tool_call_group" ? entry.calls.map((call) => `${call.id}:${call.state}`) : [];

const entries = [
  message("opening"),
  group("research", "s1", "s2"),
  group("build", "a1"),
  message("reply"),
];

test("without a presentation the conversation shows as it is", () => {
  assert.deepEqual(followProgress(entries, null), { entries, behind: false });
});

test("calls the presentation has yet to reach wait, with all that follows", () => {
  const { entries: shown, behind } = followProgress(entries, {
    waiting: new Set(["s2", "a1"]),
    working: "s1",
  });
  assert.deepEqual(
    shown.map((entry) => entry.id),
    ["opening", "research"],
  );
  assert.deepEqual(calls(shown[1]), ["s1:pending"]);
  assert.deepEqual(shown[1].kind === "tool_call_group" && shown[1].calls[0].resultItems, []);
  assert.equal(behind, true);
});

test("a sequence none of whose calls is reached is left out", () => {
  const { entries: shown } = followProgress(entries, {
    waiting: new Set(["s1", "s2", "a1"]),
    working: null,
  });
  assert.deepEqual(
    shown.map((entry) => entry.id),
    ["opening"],
  );
});

test("the answer waits while the last call's work is still shown", () => {
  const working = followProgress(entries, { waiting: new Set(), working: "a1" });
  assert.deepEqual(
    working.entries.map((entry) => entry.id),
    ["opening", "research", "build"],
  );
  assert.deepEqual(calls(working.entries[1]), ["s1:completed", "s2:completed"]);
  assert.deepEqual(calls(working.entries[2]), ["a1:pending"]);

  const done = followProgress(entries, { waiting: new Set(), working: null });
  assert.deepEqual(done, { entries, behind: false });
});

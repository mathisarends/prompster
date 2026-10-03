import { test } from "node:test";
import assert from "node:assert/strict";
import { chatReducer, createInitialChatState } from "../src/features/chat/state/chat-reducer.ts";

test("streams text and playlist updates without duplicating cards", () => {
  let state = chatReducer(createInitialChatState(), {
    type: "stream/started",
    userMessageText: "90er",
  });
  state = chatReducer(state, {
    type: "stream/event",
    event: {
      type: "message.assistant_started",
      messageId: "assistant",
      createdAt: "2026-10-03T10:00:00Z",
    },
  });
  state = chatReducer(state, {
    type: "stream/event",
    event: { type: "message.assistant_chunk", messageId: "assistant", chunk: "Dein Deck" },
  });
  const track = { id: "song", title: "Song", artist: "Artist", year: 1991 };
  for (let i = 0; i < 2; i++) {
    state = chatReducer(state, {
      type: "stream/event",
      event: { type: "playlist.track_added", playlistId: "deck", track },
    });
  }
  assert.equal(state.playlist?.tracks.length, 1);
  assert.equal(
    state.entries.find((entry) => entry.kind === "assistant_message")?.content,
    "Dein Deck",
  );
  state = chatReducer(state, { type: "stream/finished" });
  assert.equal(state.isStreaming, false);
});
test("reset clears old session state and pending onboarding", () => {
  let state = chatReducer(createInitialChatState(), {
    type: "stream/event",
    event: {
      type: "session.onboarding_question_asked",
      questionId: "question",
      question: "Welche Zeit?",
      options: ["90er"],
      isLastQuestion: true,
    },
  });
  assert.equal(state.pendingInput?.questions[0].id, "question");
  assert.deepEqual(chatReducer(state, { type: "session/reset" }), createInitialChatState());
});

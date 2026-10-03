import { test } from "node:test";
import assert from "node:assert/strict";
import {
  SpeechSession,
  type BrowserSpeechRecognition,
} from "../src/shared/ui/voice-input/speech-session.ts";

class Recognition implements BrowserSpeechRecognition {
  static current: Recognition;
  lang = "";
  continuous = false;
  interimResults = false;
  onstart: BrowserSpeechRecognition["onstart"] = null;
  onresult: BrowserSpeechRecognition["onresult"] = null;
  onerror: BrowserSpeechRecognition["onerror"] = null;
  onend: BrowserSpeechRecognition["onend"] = null;
  stopped = false;
  aborted = false;
  constructor() {
    Recognition.current = this;
  }
  start() {
    this.onstart?.();
  }
  stop() {
    this.stopped = true;
  }
  abort() {
    this.aborted = true;
  }
  result(text: string) {
    this.onresult?.({ results: [[{ transcript: text }]] });
  }
}

test("dictation waits for the final result before accepting and never sends a message", () => {
  const committed: string[] = [];
  const session = new SpeechSession(
    () => {},
    (text) => committed.push(text),
  );
  session.start(Recognition, "de-DE");
  const recognition = Recognition.current;
  assert.equal(recognition.lang, "de-DE");
  recognition.result("Musik aus den");
  session.accept();
  assert.equal(session.state.phase, "stopping");
  assert.deepEqual(committed, []);
  recognition.result("Musik aus den Neunzigern");
  recognition.onend?.();
  assert.deepEqual(committed, ["Musik aus den Neunzigern"]);
  assert.equal(session.state.phase, "idle");
});

test("cancelled and replaced sessions ignore late speech events", () => {
  const committed: string[] = [];
  const session = new SpeechSession(
    () => {},
    (text) => committed.push(text),
  );
  session.start(Recognition, "de-DE");
  const old = Recognition.current;
  const lateResult = old.onresult;
  const lateEnd = old.onend;
  session.accept();
  session.cancel();
  session.start(Recognition, "de-DE");
  lateResult?.({ results: [[{ transcript: "alter Entwurf" }]] });
  lateEnd?.();
  assert.equal(old.aborted, true);
  assert.equal(session.state.transcript, "");
  assert.equal(session.state.phase, "listening");
  assert.deepEqual(committed, []);
});

test("a natural end keeps the transcript for review; errors allow another attempt", () => {
  const committed: string[] = [];
  const session = new SpeechSession(
    () => {},
    (text) => committed.push(text),
  );
  session.start(Recognition, "de-DE");
  Recognition.current.onerror?.({ error: "not-allowed" });
  assert.equal(session.state.error, "not-allowed");
  assert.equal(session.state.phase, "idle");
  session.start(Recognition, "de-DE");
  Recognition.current.result("Disco");
  Recognition.current.onend?.();
  assert.equal(session.state.phase, "review");
  assert.deepEqual(committed, []);
  session.accept();
  assert.deepEqual(committed, ["Disco"]);
});

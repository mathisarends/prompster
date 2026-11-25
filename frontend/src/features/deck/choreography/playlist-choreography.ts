import type { ReactiveController, ReactiveControllerHost } from "lit";
import type { SessionStreamEvent } from "@/api/session-streams";
import type { ToolCallProgress } from "@features/chat/types";
import type { Feed } from "@shared/feed";
import { CueScript, type Cue, type StageTrack } from "./cues";
import { direct, openStage, rest, unfold, type Stage, type Step } from "./stage";

export type Clock = { sleep(ms: number): Promise<void> };

type Options = {
  /** The deck as the host shows it while nothing is staged. */
  tracks: () => StageTrack[];
  /** Told whenever the stage gets further with the agent's tool calls. */
  progress?: (progress: ToolCallProgress | null) => void;
  clock?: Clock;
  reducedMotion?: () => boolean;
};

const realClock: Clock = { sleep: (ms) => new Promise((resolve) => setTimeout(resolve, ms)) };
const prefersReducedMotion = () =>
  globalThis.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;

/** With this many cues waiting, the rest is shown at once instead of staged. */
const overflow = 60;
/** The fastest that steps play which must stay readable. */
const steadyTempo = 2;
/** Milliseconds an idle stage waits for the rest of a burst of events. */
const gather = 50;

/**
 * Presents the agent's work on the deck at a watchable pace.
 *
 * The session stream reports searches and deck edits faster than anyone can
 * follow, often many at once. The choreography queues them as cues and plays
 * them one after another on `stage`: it types each query into the search
 * field, shows the hits, and lets rows land, leave or be rewritten. While
 * `stage` is set the host shows it instead of the real deck; it is null again
 * once the agent's turn is over and everything was shown.
 *
 * The tempo rises with the backlog, so the stage never falls far behind. With
 * reduced motion nothing is staged and the host shows the deck as it changes.
 *
 * `progress` says which tool calls the stage has yet to reach and which one it
 * is showing, so the conversation can list a call when its work appears.
 */
export class PlaylistChoreography implements ReactiveController {
  stage: Stage | null = null;
  /** Null while nothing is staged: every call may show as it is. */
  progress: ToolCallProgress | null = null;
  private waiting = new Set<string>();
  /** The call the stage reached last, while more of its work may follow. */
  private current: string | null = null;
  private script = new CueScript();
  private queue: Cue[] = [];
  private feed?: Feed<SessionStreamEvent>;
  private unsubscribe?: () => void;
  private running = false;
  private playing = false;
  private generation = 0;
  private readonly tracks: () => StageTrack[];
  private readonly announce?: (progress: ToolCallProgress | null) => void;
  private readonly clock: Clock;
  private readonly reducedMotion: () => boolean;

  constructor(
    private host: ReactiveControllerHost,
    { tracks, progress, clock = realClock, reducedMotion = prefersReducedMotion }: Options,
  ) {
    this.tracks = tracks;
    this.announce = progress;
    this.clock = clock;
    this.reducedMotion = reducedMotion;
    host.addController(this);
  }

  hostConnected(): void {
    this.unsubscribe ??= this.feed?.subscribe(this.receive);
  }

  hostDisconnected(): void {
    this.unsubscribe?.();
    this.unsubscribe = undefined;
    this.clear();
  }

  /** Follows this stream of session events. */
  follow(feed: Feed<SessionStreamEvent> | undefined): void {
    if (feed === this.feed) {
      return;
    }
    this.unsubscribe?.();
    this.feed = feed;
    this.unsubscribe = feed?.subscribe(this.receive);
  }

  /** Tells whether the agent's turn is still running. Once it ended, the stage wraps up. */
  setRunning(running: boolean): void {
    this.running = running;
    if (!running && this.stage && !this.playing) {
      void this.play();
    }
  }

  /** Forgets the session: its searches, the waiting cues and the stage. */
  reset(): void {
    this.script = new CueScript();
    this.clear();
  }

  private clear(): void {
    this.generation++;
    this.queue = [];
    this.playing = false;
    this.waiting.clear();
    this.current = null;
    if (this.stage) {
      this.stage = null;
      this.host.requestUpdate();
    }
    this.report();
  }

  private receive = (event: SessionStreamEvent): void => {
    const cues = this.script.read(event);
    if (cues.length && !this.reducedMotion()) {
      this.stage ??= openStage(this.tracks());
      for (const cue of cues) {
        if (cue.kind === "search" || cue.kind === "call") {
          this.waiting.add(cue.callId);
        }
      }
      this.queue.push(...cues);
      if (!this.playing) {
        void this.play();
      }
    }
    this.report();
  };

  private async play(): Promise<void> {
    const generation = this.generation;
    this.playing = true;
    // Events of one burst arrive one by one; staging starts once they are all queued.
    await this.clock.sleep(gather);
    if (generation !== this.generation) {
      return;
    }
    for (;;) {
      while (this.queue.length) {
        const cue = this.queue[0];
        if (cue.kind === "sync") {
          this.queue.splice(0, 1, ...unfold(cue.tracks, this.stage!.tracks));
          continue;
        }
        if (cue.kind === "search" || cue.kind === "call") {
          this.waiting.delete(cue.callId);
          this.current = cue.callId;
          this.report();
        }
        const steps = direct(cue, {
          origin: (track) => this.script.origin(track),
          stage: () => this.stage!,
          ahead: () => this.queue.slice(1),
        });
        for (const step of steps) {
          await this.perform(step);
          if (generation !== this.generation) {
            return;
          }
        }
        this.queue.shift();
        if (cue.kind === "search") {
          this.current = null;
        }
      }
      this.report();
      if (this.running) {
        break;
      }
      await this.perform(rest);
      if (generation !== this.generation) {
        return;
      }
      if (!this.queue.length) {
        this.stage = null;
        this.host.requestUpdate();
        this.report();
        break;
      }
    }
    this.playing = false;
  }

  private async perform(step: Step): Promise<void> {
    const generation = this.generation;
    if ("until" in step) {
      // Results that never arrive must not hold up a turn that has ended.
      for (
        let waited = 0;
        !step.until() && waited < step.timeout && this.running && generation === this.generation;
        waited += 40
      ) {
        await this.clock.sleep(40);
      }
      return;
    }
    this.stage = step.apply(this.stage!);
    this.host.requestUpdate();
    this.report();
    const tempo = step.steady ? Math.min(this.tempo, steadyTempo) : this.tempo;
    const hold = this.queue.length > overflow ? 0 : step.hold / tempo;
    if (hold > 0) {
      await this.clock.sleep(hold);
    }
  }

  /** Works out how far the stage is with the tool calls and announces a change. */
  private report(): void {
    // A call that returned is done once none of its work is left to show.
    if (this.current && !this.queue.length && this.script.hasEnded(this.current)) {
      this.current = null;
    }
    const shown = this.stage?.search;
    // A search is through as soon as its hits are on stage.
    const found =
      shown?.callId === this.current && (shown.status === "results" || shown.status === "idle");
    const working = found ? null : this.current;
    const last = this.progress;
    const unchanged = this.stage
      ? last?.working === working &&
        last.waiting.size === this.waiting.size &&
        [...this.waiting].every((callId) => last.waiting.has(callId))
      : !last;
    if (unchanged) {
      return;
    }
    this.progress = this.stage ? { waiting: new Set(this.waiting), working } : null;
    this.announce?.(this.progress);
  }

  /** How much faster than normal the stage plays, so a backlog shrinks. */
  private get tempo(): number {
    const backlog = Math.max(0, this.queue.length - 2);
    return Math.max(this.running ? 1 : 2.5, Math.min(1 + backlog * 0.35, 5));
  }
}

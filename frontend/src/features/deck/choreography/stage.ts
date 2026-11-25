import type { Cue, SearchCue, SearchHit, StagedCue, StageTrack } from "./cues";

/** The search field as the agent currently drives it. */
export type StageSearch = {
  callId: string;
  /** The part of the query typed so far. */
  query: string;
  /** `results` lays the hits over the deck; `idle` leaves only the query in the field. */
  status: "typing" | "searching" | "results" | "idle";
  hits: SearchHit[];
  /** Keys of the hits the agent took into the deck. */
  picked: string[];
};

export type RowMark = "added" | "rewritten" | "leaving";

/** What the deck panel shows while the agent works: the deck as presented so far. */
export type Stage = {
  tracks: StageTrack[];
  marks: Record<string, RowMark>;
  /** A row whose title is still being typed out. */
  rewrite: { trackId: string; title: string } | null;
  search: StageSearch | null;
  /** Tracks the agent already marked in the search and that have yet to land. */
  chosen: string[];
  /** The row the agent touched last, to keep it in view. */
  focus: string | null;
};

/**
 * One visible change and how long it stays before the next, at normal tempo.
 * A `steady` step is sped up less, so the search stays readable in a backlog.
 */
export type Step =
  | { apply: (stage: Stage) => Stage; hold: number; steady?: boolean }
  | { until: () => boolean; timeout: number };

export const openStage = (tracks: StageTrack[]): Stage => ({
  tracks,
  marks: {},
  rewrite: null,
  search: null,
  chosen: [],
  focus: null,
});

/** Milliseconds at normal tempo. Typing is capped so long text stays brief. */
export const pacing = {
  open: 180,
  key: 34,
  typing: 900,
  recallKey: 12,
  recall: 260,
  searching: 240,
  patience: 6000,
  results: 900,
  noResults: 320,
  fold: 160,
  pick: 170,
  chosen: 320,
  land: 130,
  leave: 360,
  rewriteKey: 16,
  rewriting: 420,
  settle: 160,
  reorder: 320,
  close: 420,
} as const;

/** Hits listed under the search field. */
export const visibleHits = 5;

type Origin = (track: StageTrack) => SearchCue | undefined;

/** What the director knows besides the cue it stages. */
export type Scene = {
  /** The search that showed the agent a track, if any. */
  origin: Origin;
  /** The stage as it is when asked. */
  stage: () => Stage;
  /** The cues waiting after the one being staged. */
  ahead: () => readonly Cue[];
};

/**
 * Splits a whole new deck into the edits that lead there from the staged one:
 * tracks leave, new ones land, then the deck takes its order.
 */
export const unfold = (tracks: StageTrack[], staged: StageTrack[]): StagedCue[] => {
  const kept = new Set(tracks.map((track) => track.id));
  const known = new Set(staged.map((track) => track.id));
  return [
    ...staged
      .filter((track) => !kept.has(track.id))
      .map((track) => ({ kind: "remove" as const, trackId: track.id })),
    ...tracks
      .filter((track) => !known.has(track.id))
      .map((track) => ({ kind: "add" as const, track })),
    { kind: "arrange", tracks },
  ];
};

/** Stages one cue as the steps that present it. */
export function* direct(cue: StagedCue, { origin, stage, ahead }: Scene): Generator<Step> {
  switch (cue.kind) {
    case "search":
      yield* search(cue);
      return;
    case "add":
      // The agent marks everything it is about to add in the search first, so
      // the hits never cover the rows while those land.
      if (!stage().chosen.includes(cue.track.id)) {
        yield* choose([cue.track, ...comingAdds(ahead())], origin, stage);
      }
      yield land(cue.track);
      return;
    case "remove":
      yield* leave(cue.trackId, stage);
      return;
    case "replace":
      yield* choose([cue.track], origin, stage);
      yield* rewrite(cue.trackId, cue.track, stage);
      return;
    case "arrange": {
      const moved = stage().tracks.some((track, index) => track.id !== cue.tracks[index]?.id);
      yield {
        apply: (current) => ({ ...current, tracks: cue.tracks, focus: null }),
        hold: moved ? pacing.reorder : 0,
      };
      return;
    }
  }
}

/** Closes the search field once the agent is done. */
export const rest: Step = {
  apply: (stage) => ({ ...stage, search: null, chosen: [], focus: null }),
  hold: pacing.close,
};

/** Takes the hits away again; the query stays in the field. */
const fold: Step = {
  apply: (stage) => withSearch(stage, { status: "idle" }),
  hold: pacing.fold,
};

const comingAdds = (ahead: readonly Cue[]): StageTrack[] => {
  const end = ahead.findIndex((cue) => cue.kind !== "add");
  return (end === -1 ? ahead : ahead.slice(0, end)).flatMap((cue) =>
    cue.kind === "add" ? [cue.track] : [],
  );
};

function* search(cue: SearchCue): Generator<Step> {
  yield* type(cue, pacing.key, pacing.typing, pacing.open);
  yield { apply: (stage) => withSearch(stage, { status: "searching" }), hold: pacing.searching };
  yield { until: () => cue.settled, timeout: pacing.patience };
  yield {
    apply: (stage) =>
      withSearch(stage, { status: "results", hits: cue.hits.slice(0, visibleHits) }),
    hold: cue.hits.length ? pacing.results : pacing.noResults,
    steady: true,
  };
  yield fold;
}

/** Types the cue's query into a cleared search field. */
function* type(cue: SearchCue, key: number, limit: number, open: number): Generator<Step> {
  yield {
    apply: (stage) => ({
      ...stage,
      search: { callId: cue.callId, query: "", status: "typing", hits: [], picked: [] },
    }),
    hold: open,
  };
  const hold = Math.min(key, limit / cue.query.length);
  for (let length = 1; length <= cue.query.length; length++) {
    yield { apply: (stage) => withSearch(stage, { query: cue.query.slice(0, length) }), hold };
  }
}

/**
 * Marks the tracks in the searches that showed them, one search after the
 * other, then takes the hits away so the rows are free to change.
 */
function* choose(tracks: StageTrack[], origin: Origin, stage: () => Stage): Generator<Step> {
  let marked = false;
  for (const source of new Set(tracks.map(origin))) {
    for (const track of tracks) {
      if (source && origin(track) === source) {
        yield* pick(track, source, stage);
        marked = true;
      }
    }
  }
  const ids = tracks.map((track) => track.id);
  yield {
    apply: (current) => ({ ...current, chosen: [...current.chosen, ...ids] }),
    hold: marked ? pacing.chosen : 0,
    steady: true,
  };
  if (marked) {
    yield fold;
  }
}

/** Marks the track among its search's hits, bringing that search back if needed. */
function* pick(track: StageTrack, source: SearchCue, stage: () => Stage): Generator<Step> {
  const key = track.spotifyUri!;
  if (stage().search?.callId !== source.callId) {
    yield* type(source, pacing.recallKey, pacing.recall, 0);
    const onStage = new Set(stage().tracks.map((candidate) => candidate.spotifyUri));
    yield {
      apply: (current) =>
        withSearch(current, {
          picked: source.hits.filter((hit) => onStage.has(hit.key)).map((hit) => hit.key),
        }),
      hold: 0,
    };
  }
  const listed = stage().search!.hits;
  yield {
    apply: (current) =>
      withSearch(current, {
        status: "results",
        hits: listed.some((hit) => hit.key === key) ? listed : hitsAround(source.hits, key),
      }),
    hold: 0,
  };
  yield {
    apply: (current) => withSearch(current, { picked: [...(current.search?.picked ?? []), key] }),
    hold: pacing.pick,
    steady: true,
  };
}

const land = (track: StageTrack): Step => ({
  apply: (stage) => ({
    ...stage,
    tracks: stage.tracks.some((candidate) => candidate.id === track.id)
      ? stage.tracks.map((candidate) => (candidate.id === track.id ? track : candidate))
      : [...stage.tracks, track],
    marks: { ...stage.marks, [track.id]: "added" },
    chosen: stage.chosen.filter((id) => id !== track.id),
    focus: track.id,
  }),
  hold: pacing.land,
});

function* leave(trackId: string, stage: () => Stage): Generator<Step> {
  if (!stage().tracks.some((track) => track.id === trackId)) {
    return;
  }
  yield {
    apply: (current) => ({
      ...current,
      marks: { ...current.marks, [trackId]: "leaving" },
      focus: trackId,
    }),
    hold: pacing.leave,
  };
  yield {
    apply: (current) => ({
      ...current,
      tracks: current.tracks.filter((track) => track.id !== trackId),
      focus: null,
    }),
    hold: 0,
  };
}

/** Swaps a row for another track and types the new title into it. */
function* rewrite(trackId: string, track: StageTrack, stage: () => Stage): Generator<Step> {
  if (!stage().tracks.some((candidate) => candidate.id === trackId)) {
    yield land(track);
    return;
  }
  const hold = Math.min(pacing.rewriteKey, pacing.rewriting / track.title.length);
  for (let length = 0; length <= track.title.length; length++) {
    yield {
      apply: (current) => ({
        ...current,
        tracks: current.tracks.map((candidate) => (candidate.id === trackId ? track : candidate)),
        marks: { ...current.marks, [track.id]: "rewritten" },
        rewrite: { trackId: track.id, title: track.title.slice(0, length) },
        chosen: current.chosen.filter((id) => id !== track.id),
        focus: track.id,
      }),
      hold,
    };
  }
  yield { apply: (current) => ({ ...current, rewrite: null }), hold: pacing.settle };
}

const withSearch = (stage: Stage, patch: Partial<StageSearch>): Stage =>
  stage.search ? { ...stage, search: { ...stage.search, ...patch } } : stage;

/** The hits to list so that the one with `key` is among them. */
const hitsAround = (hits: SearchHit[], key: string): SearchHit[] => {
  const index = hits.findIndex((hit) => hit.key === key);
  const start = Math.max(0, Math.min(index - visibleHits + 1, hits.length - visibleHits));
  return hits.slice(start, start + visibleHits);
};

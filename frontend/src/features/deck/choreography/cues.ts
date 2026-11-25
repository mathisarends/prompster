import type { PlaylistTrackResponse, SessionStreamEvent } from "@/api/session-streams";

export type StageTrack = PlaylistTrackResponse;

/** One Spotify result the agent saw. `key` is its track URI when it has one. */
export type SearchHit = {
  key: string;
  title: string;
  artist?: string | null;
  coverUrl?: string | null;
};

/**
 * A search the agent runs. Its results arrive later: the script fills `hits`
 * and sets `settled` on the cue it already handed out.
 */
export type SearchCue = {
  kind: "search";
  callId: string;
  query: string;
  hits: SearchHit[];
  settled: boolean;
};

/** One thing the agent did that the stage can present. */
export type StagedCue =
  | SearchCue
  /** A tool call with nothing to type. The deck edits after it are its work. */
  | { kind: "call"; callId: string }
  | { kind: "add"; track: StageTrack }
  | { kind: "remove"; trackId: string }
  | { kind: "replace"; trackId: string; track: StageTrack }
  /** Puts the deck into this order; every track is already on stage. */
  | { kind: "arrange"; tracks: StageTrack[] };

/** What the stream reports, in order. `sync` replaces the whole deck at once. */
export type Cue = StagedCue | { kind: "sync"; tracks: StageTrack[] };

const queryArgument: Record<string, string> = {
  search_tracks: "query",
  search_playlists: "query",
  get_spotify_playlist_tracks: "playlist_name",
};

/**
 * Reads a session stream as cues for the deck's choreography.
 *
 * It also remembers which search showed which track, so a later add can be
 * staged as a pick from that search.
 */
export class CueScript {
  private calls = new Set<string>();
  private ended = new Set<string>();
  private searches = new Map<string, SearchCue>();
  private origins = new Map<string, SearchCue>();

  read(event: SessionStreamEvent): Cue[] {
    switch (event.type) {
      case "tool_call.sequence_added":
        // The sequence is sent again with every call added to it.
        return event.sequence.calls.flatMap((call): Cue[] => {
          if (call.state !== "pending" || this.calls.has(call.id)) {
            return [];
          }
          this.calls.add(call.id);
          const argument = queryArgument[call.function.name];
          const query = argument ? call.function.arguments[argument] : undefined;
          if (typeof query !== "string" || !query.trim()) {
            return [{ kind: "call", callId: call.id }];
          }
          const cue: SearchCue = {
            kind: "search",
            callId: call.id,
            query: query.trim(),
            hits: [],
            settled: false,
          };
          this.searches.set(call.id, cue);
          return [cue];
        });
      case "tool_call.resolved":
        this.ended.add(event.toolCallId);
        this.settle(
          event.toolCallId,
          (event.resultItems ?? []).map((item, index) => ({
            key: item.trackUri ?? `${event.toolCallId}:${index}`,
            title: item.title,
            artist: item.artist,
            coverUrl: item.coverUrl,
          })),
        );
        return [];
      case "tool_call.failed":
        this.ended.add(event.toolCallId);
        this.settle(event.toolCallId, []);
        return [];
      case "playlist.track_added":
        return [{ kind: "add", track: event.track }];
      case "playlist.track_removed":
        return [{ kind: "remove", trackId: event.trackId }];
      case "playlist.track_replaced":
        return [{ kind: "replace", trackId: event.trackId, track: event.track }];
      case "playlist.set":
        return [{ kind: "sync", tracks: event.playlist.tracks }];
      case "session.snapshot":
        return [{ kind: "sync", tracks: event.session.playlist?.tracks ?? [] }];
      default:
        return [];
    }
  }

  /** The search that showed the agent this track, if it ran in this session. */
  origin(track: StageTrack): SearchCue | undefined {
    return track.spotifyUri ? this.origins.get(track.spotifyUri) : undefined;
  }

  /** Whether the call has returned, with a result or a failure. */
  hasEnded(callId: string): boolean {
    return this.ended.has(callId);
  }

  private settle(callId: string, hits: SearchHit[]): void {
    const cue = this.searches.get(callId);
    if (!cue || cue.settled) {
      return;
    }
    cue.hits = hits;
    cue.settled = true;
    for (const hit of hits) {
      if (!this.origins.has(hit.key)) {
        this.origins.set(hit.key, cue);
      }
    }
  }
}

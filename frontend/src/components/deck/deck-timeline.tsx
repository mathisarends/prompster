import { useMemo } from "react";
import { CalendarRange, Disc3 } from "lucide-react";

import { cn } from "@/lib/utils";
import type { PlaylistTrack } from "@/lib/playlist-track";

type DeckTimelineProps = {
  tracks: PlaylistTrack[];
};

type DecadeBucket = {
  decade: number;
  label: string;
  tracks: PlaylistTrack[];
};

const parseYear = (value: string): number | null => {
  const year = Number.parseInt(value, 10);
  return Number.isFinite(year) && year > 0 ? year : null;
};

export const DeckTimeline = ({ tracks }: DeckTimelineProps) => {
  const { buckets, undated, peakDecade, yearSpan } = useMemo(() => {
    const datedTracks = tracks
      .map((track) => ({ track, year: parseYear(track.year) }))
      .filter(
        (entry): entry is { track: PlaylistTrack; year: number } =>
          entry.year !== null,
      );
    const undatedTracks = tracks.filter(
      (track) => parseYear(track.year) === null,
    );

    if (datedTracks.length === 0) {
      return {
        buckets: [] as DecadeBucket[],
        undated: undatedTracks,
        peakDecade: null as number | null,
        yearSpan: null as { min: number; max: number } | null,
      };
    }

    const years = datedTracks.map((entry) => entry.year);
    const minYear = Math.min(...years);
    const maxYear = Math.max(...years);
    const minDecade = Math.floor(minYear / 10) * 10;
    const maxDecade = Math.floor(maxYear / 10) * 10;

    // Fill every decade in the range so gaps stay visible.
    const result: DecadeBucket[] = [];
    for (let decade = minDecade; decade <= maxDecade; decade += 10) {
      const decadeTracks = datedTracks
        .filter((entry) => Math.floor(entry.year / 10) * 10 === decade)
        .sort((a, b) => a.year - b.year)
        .map((entry) => entry.track);
      result.push({
        decade,
        label: `${decade}er`,
        tracks: decadeTracks,
      });
    }

    const peak = result.reduce<DecadeBucket | null>((best, bucket) => {
      if (!best || bucket.tracks.length > best.tracks.length) return bucket;
      return best;
    }, null);

    return {
      buckets: result,
      undated: undatedTracks,
      peakDecade: peak && peak.tracks.length > 0 ? peak.decade : null,
      yearSpan: { min: minYear, max: maxYear },
    };
  }, [tracks]);

  if (tracks.length === 0) {
    return (
      <div className="grid min-h-0 flex-1 place-items-center px-6 text-center">
        <div className="max-w-xs">
          <div className="mx-auto grid size-14 place-items-center rounded-md bg-primary/12 text-primary">
            <CalendarRange className="size-6" />
          </div>
          <p className="mt-4 text-sm font-semibold">Noch keine Songs</p>
          <p className="mt-1 text-xs leading-5 text-muted-foreground">
            Sobald Songs in der Playlist sind, zeigt die Timeline, um welche
            Jahre sie sich gruppieren.
          </p>
        </div>
      </div>
    );
  }

  const maxCount = buckets.reduce(
    (max, bucket) => Math.max(max, bucket.tracks.length),
    0,
  );

  return (
    <div className="prompster-scrollbar flex min-h-0 flex-1 flex-col gap-4 overflow-auto pt-1">
      {yearSpan ? (
        <div className="flex shrink-0 items-center justify-between rounded-md border border-white/[0.08] bg-white/[0.035] px-3 py-2.5">
          <div>
            <p className="text-[11px] uppercase tracking-wide text-muted-foreground">
              Zeitraum
            </p>
            <p className="mt-0.5 text-sm font-semibold tabular-nums text-foreground">
              {yearSpan.min} – {yearSpan.max}
            </p>
          </div>
          {peakDecade !== null ? (
            <div className="text-right">
              <p className="text-[11px] uppercase tracking-wide text-muted-foreground">
                Schwerpunkt
              </p>
              <p className="mt-0.5 text-sm font-semibold tabular-nums text-primary">
                {peakDecade}er
              </p>
            </div>
          ) : null}
        </div>
      ) : null}

      <div className="flex flex-col">
        {buckets.map((bucket, index) => (
          <DecadeRow
            key={bucket.decade}
            bucket={bucket}
            maxCount={maxCount}
            isPeak={bucket.decade === peakDecade}
            isLast={index === buckets.length - 1 && undated.length === 0}
          />
        ))}

        {undated.length > 0 ? (
          <UndatedRow tracks={undated} />
        ) : null}
      </div>
    </div>
  );
};

type DecadeRowProps = {
  bucket: DecadeBucket;
  maxCount: number;
  isPeak: boolean;
  isLast: boolean;
};

const DecadeRow = ({ bucket, maxCount, isPeak, isLast }: DecadeRowProps) => {
  const count = bucket.tracks.length;
  const isEmpty = count === 0;
  const barWidth = maxCount > 0 ? Math.round((count / maxCount) * 100) : 0;

  return (
    <div className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-3">
      <div className="relative flex flex-col items-center">
        <span
          className={cn(
            "mt-1 size-2.5 shrink-0 rounded-full ring-2 ring-background",
            isEmpty
              ? "bg-white/15"
              : isPeak
                ? "bg-primary"
                : "bg-muted-foreground",
          )}
        />
        {!isLast ? (
          <span className="w-px flex-1 bg-white/[0.08]" aria-hidden />
        ) : null}
      </div>

      <div className="min-w-0 pb-5">
        <div className="flex items-center gap-2">
          <span
            className={cn(
              "text-sm font-semibold tabular-nums",
              isEmpty ? "text-muted-foreground/60" : "text-foreground",
            )}
          >
            {bucket.label}
          </span>
          {!isEmpty ? (
            <span className="text-sm text-muted-foreground tabular-nums">
              {count} {count === 1 ? "Song" : "Songs"}
            </span>
          ) : null}
        </div>

        <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-white/[0.05]">
          <div
            className={cn(
              "h-full rounded-full transition-all",
              isPeak ? "bg-primary" : "bg-muted-foreground/55",
            )}
            style={{ width: `${barWidth}%` }}
          />
        </div>

        {!isEmpty ? (
          <ul className="mt-3 space-y-1">
            {bucket.tracks.map((track) => (
              <TimelineTrack
                key={track.id}
                track={track}
                showYear
                accent={isPeak}
              />
            ))}
          </ul>
        ) : null}
      </div>
    </div>
  );
};

type TimelineTrackProps = {
  track: PlaylistTrack;
  showYear?: boolean;
  accent?: boolean;
};

const TimelineTrack = ({ track, showYear, accent }: TimelineTrackProps) => (
  <li className="group flex items-center gap-3 rounded-md px-1.5 py-1.5 transition-colors hover:bg-white/[0.04]">
    <div
      className={cn(
        "relative size-10 shrink-0 overflow-hidden rounded-[5px] bg-white/[0.06] shadow-sm ring-1 transition",
        accent ? "ring-primary/30" : "ring-white/[0.06]",
      )}
    >
      {track.coverUrl ? (
        <img
          src={track.coverUrl}
          alt={`${track.title} Cover`}
          className="h-full w-full object-cover transition group-hover:scale-105"
          loading="lazy"
        />
      ) : (
        <div className="grid h-full w-full place-items-center">
          <Disc3 className="size-4 text-muted-foreground/50" />
        </div>
      )}
    </div>
    <div className="min-w-0 flex-1">
      <p className="truncate text-sm font-semibold leading-tight text-foreground">
        {track.artist}
      </p>
      <p className="mt-0.5 truncate text-xs leading-tight text-muted-foreground">
        {track.title}
      </p>
    </div>
    {showYear && track.year ? (
      <span
        className={cn(
          "shrink-0 rounded-full px-2 py-0.5 text-[11px] font-semibold tabular-nums",
          accent
            ? "bg-primary/12 text-primary"
            : "bg-white/[0.05] text-muted-foreground",
        )}
      >
        {track.year}
      </span>
    ) : null}
  </li>
);

const UndatedRow = ({ tracks }: { tracks: PlaylistTrack[] }) => (
  <div className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-3">
    <div className="flex flex-col items-center">
      <span className="mt-1 size-2.5 shrink-0 rounded-full bg-white/15 ring-2 ring-background" />
    </div>
    <div className="min-w-0">
      <span className="text-sm font-semibold text-muted-foreground/60">
        Ohne Jahr
      </span>
      <span className="ml-2 text-sm text-muted-foreground tabular-nums">
        {tracks.length} {tracks.length === 1 ? "Song" : "Songs"}
      </span>
      <ul className="mt-3 space-y-1">
        {tracks.map((track) => (
          <TimelineTrack key={track.id} track={track} />
        ))}
      </ul>
    </div>
  </div>
);

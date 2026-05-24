import { Skeleton } from "@/components/ui/skeleton";

const ROW_COUNT = 6;

const titleWidths = [
  "w-[68%]",
  "w-[58%]",
  "w-[74%]",
  "w-[62%]",
  "w-[71%]",
  "w-[55%]",
];
const subtitleWidths = [
  "w-[52%]",
  "w-[46%]",
  "w-[49%]",
  "w-[44%]",
  "w-[53%]",
  "w-[41%]",
];

export const SearchResultsSkeleton = () => (
  <div
    className="space-y-1"
    aria-label="Spotify Suchergebnisse werden geladen"
    role="status"
  >
    {Array.from({ length: ROW_COUNT }).map((_, index) => (
      <div
        key={`search-track-skeleton-${index}`}
        className="grid grid-cols-[40px_minmax(0,1fr)_auto] items-center gap-3 rounded-md px-2 py-2"
      >
        <Skeleton className="size-10 rounded-[4px]" />
        <div className="space-y-2">
          <Skeleton
            className={`h-4 ${titleWidths[index % titleWidths.length]}`}
          />
          <Skeleton
            className={`h-3 ${subtitleWidths[index % subtitleWidths.length]}`}
          />
        </div>
        <Skeleton className="size-8 rounded-md bg-foreground/15" />
      </div>
    ))}
  </div>
);

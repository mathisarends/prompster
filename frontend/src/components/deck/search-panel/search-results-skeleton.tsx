import { Skeleton } from "@/components/ui/skeleton";

const ROW_COUNT = 6;

export const SearchResultsSkeleton = () => (
  <div className="space-y-1" aria-label="Spotify Suchergebnisse werden geladen" role="status">
    {Array.from({ length: ROW_COUNT }).map((_, index) => (
      <div
        key={`search-track-skeleton-${index}`}
        className="grid grid-cols-[40px_minmax(0,1fr)_auto] items-center gap-3 rounded-md px-2 py-2"
      >
        <Skeleton className="size-10 rounded-[4px]" />
        <div className="space-y-2">
          <Skeleton className="h-4 w-[68%]" />
          <Skeleton className="h-3 w-[52%]" />
        </div>
        <Skeleton className="size-8 rounded-md" />
      </div>
    ))}
  </div>
);
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

const titleWidths = ["w-[68%]", "w-[58%]", "w-[72%]", "w-[61%]"];
const subtitleWidths = ["w-[48%]", "w-[41%]", "w-[53%]", "w-[45%]"];

export const AttachmentSearchSkeleton = () => (
  <div
    className="space-y-1"
    aria-label="Spotify Anhänge werden geladen"
    role="status"
  >
    {Array.from({ length: 5 }).map((_, index) => (
      <div
        key={`attachment-search-skeleton-${index}`}
        className="grid grid-cols-[36px_minmax(0,1fr)_auto] items-center gap-2.5 rounded-md px-2 py-1.5"
      >
        <Skeleton
          className={cn("size-9", index > 2 ? "rounded-full" : "rounded-[4px]")}
        />
        <div className="space-y-2">
          <Skeleton
            className={cn("h-3.5", titleWidths[index % titleWidths.length])}
          />
          <Skeleton
            className={cn("h-3", subtitleWidths[index % subtitleWidths.length])}
          />
        </div>
        <Skeleton className="size-4 rounded-full bg-foreground/15" />
      </div>
    ))}
  </div>
);

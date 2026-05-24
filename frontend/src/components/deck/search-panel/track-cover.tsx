import type { ReactNode } from "react";

type TrackCoverProps = {
  src?: string | null;
  alt: string;
  fallback?: ReactNode;
};

export const TrackCover = ({ src, alt, fallback }: TrackCoverProps) => (
  <div className="grid size-10 shrink-0 place-items-center overflow-hidden rounded-[4px] bg-white/[0.06] text-muted-foreground shadow-sm ring-1 ring-white/[0.04]">
    {src ? (
      <img
        src={src}
        alt={alt}
        className="h-full w-full object-cover"
        loading="lazy"
      />
    ) : (
      fallback
    )}
  </div>
);

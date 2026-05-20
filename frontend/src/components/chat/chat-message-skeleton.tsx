import { Skeleton } from "@/components/ui/skeleton";

type ChatMessageSkeletonProps = {
  variant: "user" | "assistant";
};

export const ChatMessageSkeleton = ({ variant }: ChatMessageSkeletonProps) => {
  if (variant === "user") {
    return (
      <div className="ml-auto flex max-w-[82%] flex-col gap-2 rounded-2xl bg-white/10 px-4 py-3">
        <Skeleton className="h-4 w-64 bg-white/15" />
        <Skeleton className="h-4 w-56 bg-white/15" />
        <Skeleton className="h-4 w-48 bg-white/15" />
        <Skeleton className="h-4 w-40 bg-white/15" />
      </div>
    );
  }

  return (
    <div className="flex max-w-[82%] flex-col gap-2 px-1 py-2">
      <Skeleton className="h-4 w-full max-w-md" />
      <Skeleton className="h-4 w-2/3" />
      <Skeleton className="h-4 w-full max-w-md" />
      <Skeleton className="h-4 w-3/5" />
      <Skeleton className="h-4 w-2/5" />
    </div>
  );
};

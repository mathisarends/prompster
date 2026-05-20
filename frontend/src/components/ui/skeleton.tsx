import { cn } from "@/lib/utils";

type SkeletonProps = React.HTMLAttributes<HTMLDivElement>;

export const Skeleton = ({ className, ...props }: SkeletonProps) => (
  <div
    className={cn("animate-pulse rounded-md bg-foreground/10", className)}
    {...props}
  />
);

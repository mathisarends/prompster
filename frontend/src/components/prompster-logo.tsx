import { cn } from "@/lib/utils";

type PrompsterLogoProps = {
  className?: string;
  iconClassName?: string;
  titleClassName?: string;
  subtitle?: string;
  subtitleClassName?: string;
};

export const PrompsterLogo = ({
  className,
  iconClassName,
  titleClassName,
  subtitle,
  subtitleClassName,
}: PrompsterLogoProps) => {
  return (
    <div className={cn("flex items-center gap-3", className)}>
      <div
        className={cn(
          "grid size-9 place-items-center rounded-xl bg-sidebar-accent text-lg font-bold text-sidebar-accent-foreground",
          iconClassName,
        )}
      >
        P
      </div>
      <div className="min-w-0">
        <p
          className={cn(
            "truncate text-base font-semibold tracking-tight",
            titleClassName,
          )}
        >
          Prompster
        </p>
        {subtitle ? (
          <p className={cn("truncate text-xs text-muted-foreground", subtitleClassName)}>
            {subtitle}
          </p>
        ) : null}
      </div>
    </div>
  );
};
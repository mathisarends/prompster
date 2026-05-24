import { cn } from "@/lib/utils";

type PrompsterLogoProps = {
  className?: string;
  iconClassName?: string;
  titleClassName?: string;
  subtitle?: string;
  subtitleClassName?: string;
};

const PrompsterMark = ({ className }: { className?: string }) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 48 46"
    fill="none"
    aria-hidden="true"
    className={className}
  >
    <path
      fill="#863bff"
      d="M25.946 44.938c-.664.845-2.021.375-2.021-.698V33.937a2.26 2.26 0 0 0-2.262-2.262H10.287c-.92 0-1.456-1.04-.92-1.788l7.48-10.471c1.07-1.497 0-3.578-1.842-3.578H1.237c-.92 0-1.456-1.04-.92-1.788L10.013.474c.214-.297.556-.474.92-.474h28.894c.92 0 1.456 1.04.92 1.788l-7.48 10.471c-1.07 1.498 0 3.579 1.842 3.579h11.377c.943 0 1.473 1.088.89 1.83L25.947 44.94z"
    />
  </svg>
);

export const PrompsterLogo = ({
  className,
  iconClassName,
  titleClassName,
  subtitle,
  subtitleClassName,
}: PrompsterLogoProps) => {
  return (
    <div className={cn("flex items-center gap-2.5", className)}>
      <div
        className={cn(
          "grid size-7 place-items-center",
          iconClassName,
        )}
      >
        <PrompsterMark className="size-5" />
      </div>
      <div className="min-w-0">
        <p
          className={cn(
            "truncate text-sm font-semibold tracking-tight",
            titleClassName,
          )}
        >
          Prompster
        </p>
        {subtitle ? (
          <p
            className={cn(
              "truncate text-xs text-muted-foreground",
              subtitleClassName,
            )}
          >
            {subtitle}
          </p>
        ) : null}
      </div>
    </div>
  );
};

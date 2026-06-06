import type { ChangeEventHandler, ComponentProps, Ref } from "react";
import { Search, X } from "lucide-react";

import { Input } from "@/shared/ui/input";
import { cn } from "@/shared/lib/utils";

type SearchBarProps = Omit<
  ComponentProps<"input">,
  "className" | "onChange"
> & {
  onChange: ChangeEventHandler<HTMLInputElement>;
  inputRef?: Ref<HTMLInputElement>;
  containerClassName?: string;
  inputClassName?: string;
  iconClassName?: string;
  onClear?: () => void;
};

export const SearchBar = ({
  onChange,
  inputRef,
  containerClassName,
  inputClassName,
  iconClassName,
  onClear,
  value,
  ...props
}: SearchBarProps) => {
  const showClearButton = Boolean(onClear) && Boolean(value);

  return (
    <div className={cn("relative", containerClassName)}>
      <Search
        className={cn(
          "pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground",
          iconClassName,
        )}
      />
      <Input
        ref={inputRef}
        onChange={onChange}
        value={value}
        autoCapitalize="none"
        autoComplete="off"
        autoCorrect="off"
        spellCheck={false}
        className={cn(
          "rounded-md border-transparent bg-white/[0.04] pl-9 text-sm shadow-none placeholder:text-muted-foreground/70 focus-visible:border-transparent",
          showClearButton ? "pr-9" : null,
          inputClassName,
        )}
        {...props}
      />
      {showClearButton ? (
        <button
          type="button"
          onClick={onClear}
          aria-label="Suche leeren"
          tabIndex={-1}
          className="absolute right-1.5 top-1/2 grid size-6 -translate-y-1/2 place-items-center rounded-md text-muted-foreground transition-colors hover:bg-white/[0.08] hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <X className="size-3.5" />
        </button>
      ) : null}
    </div>
  );
};

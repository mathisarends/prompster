import type { ChangeEventHandler, ComponentProps, Ref } from "react";
import { Search } from "lucide-react";

import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

type SearchBarProps = Omit<
  ComponentProps<"input">,
  "className" | "onChange"
> & {
  onChange: ChangeEventHandler<HTMLInputElement>;
  inputRef?: Ref<HTMLInputElement>;
  containerClassName?: string;
  inputClassName?: string;
  iconClassName?: string;
};

export const SearchBar = ({
  onChange,
  inputRef,
  containerClassName,
  inputClassName,
  iconClassName,
  ...props
}: SearchBarProps) => {
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
        autoCapitalize="none"
        autoComplete="off"
        autoCorrect="off"
        spellCheck={false}
        className={cn(
          "rounded-md border-transparent bg-white/[0.04] pl-9 text-sm shadow-none placeholder:text-muted-foreground/70 focus-visible:border-transparent",
          inputClassName,
        )}
        {...props}
      />
    </div>
  );
};

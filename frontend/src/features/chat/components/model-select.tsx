import { useEffect, useMemo, useState } from "react";
import { Check, ChevronDown, Cpu } from "lucide-react";

import { useListLlmOptions } from "@/api/generated/llm-options/llm-options";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/shared/ui/dropdown-menu";
import { cn } from "@/shared/lib/utils";

type ModelSelectProps = {
  value?: string;
  onChange?: (modelId: string) => void;
  disabled?: boolean;
  className?: string;
};

export const ModelSelect = ({
  value,
  onChange,
  disabled = false,
  className,
}: ModelSelectProps) => {
  const { data, isLoading } = useListLlmOptions();
  const options = useMemo(() => data?.items ?? [], [data]);

  const [internalValue, setInternalValue] = useState<string | undefined>(value);
  const selectedId = value ?? internalValue;

  // Pre-select the backend's default model once the options have loaded.
  useEffect(() => {
    if (selectedId || options.length === 0) return;

    const fallback = options.find((option) => option.isDefault) ?? options[0];
    setInternalValue(fallback.id);
    onChange?.(fallback.id);
  }, [options, selectedId, onChange]);

  const selectedOption = useMemo(
    () => options.find((option) => option.id === selectedId),
    [options, selectedId],
  );

  const handleSelect = (modelId: string) => {
    setInternalValue(modelId);
    onChange?.(modelId);
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        disabled={disabled || isLoading || options.length === 0}
        aria-label="Modell auswählen"
        className={cn(
          "inline-flex h-8 items-center gap-1.5 rounded-md px-2 text-sm text-muted-foreground transition-colors",
          "hover:bg-muted hover:text-foreground aria-expanded:bg-muted aria-expanded:text-foreground",
          "focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50",
          className,
        )}
      >
        <Cpu className="size-4 shrink-0" />
        <span className="max-w-40 truncate">
          {selectedOption?.label ?? "Modell"}
        </span>
        <ChevronDown className="size-3.5 shrink-0 opacity-70" />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" side="top" className="min-w-52">
        {options.map((option) => (
          <DropdownMenuItem
            key={option.id}
            onClick={() => handleSelect(option.id)}
          >
            <span className="flex-1 truncate">{option.label}</span>
            {option.id === selectedId && <Check className="size-4 shrink-0" />}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
};

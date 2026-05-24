import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type AttachmentFilterPillProps<TValue extends string> = {
  value: TValue;
  label: string;
  isActive: boolean;
  onSelect: (value: TValue) => void;
};

export function AttachmentFilterPill<TValue extends string>({
  value,
  label,
  isActive,
  onSelect,
}: AttachmentFilterPillProps<TValue>) {
  return (
    <Button
      type="button"
      variant="ghost"
      size="xs"
      aria-pressed={isActive}
      onClick={() => onSelect(value)}
      className={cn(
        "h-6 rounded-full border px-2 text-[11px]",
        isActive
          ? "border-primary/35 bg-primary/15 text-primary hover:bg-primary/20 hover:text-primary"
          : "border-white/[0.08] bg-white/[0.03] text-muted-foreground hover:bg-white/[0.07] hover:text-foreground",
      )}
    >
      {label}
    </Button>
  );
}

import type { ShortcutKey } from "@/components/sidebar/keyboard-shortcut-hint";
import { usePlatform } from "@/hooks/usePlatform";

type SidebarInlineShortcutKeysProps = {
  keys: ShortcutKey[];
};

export const SidebarInlineShortcutKeys = ({
  keys,
}: SidebarInlineShortcutKeysProps) => {
  const { formatShortcutKey } = usePlatform();

  return (
    <span className="ml-auto flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
      {keys.map((key, index) => (
        <kbd
          key={`${key}-${index}`}
          className="min-w-5 rounded border border-sidebar-border/60 bg-sidebar px-1.5 py-0.5 text-center text-[10px] font-semibold leading-none text-sidebar-foreground/80"
        >
          {formatShortcutKey(key)}
        </kbd>
      ))}
    </span>
  );
};

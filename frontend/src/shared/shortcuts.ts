type Shortcut = { key: string; mod?: boolean; alt?: boolean; shift?: boolean };

export const shortcuts = {
  sidebar: { key: "b", mod: true },
  newDeck: { key: "n", alt: true },
  deck: { key: "d", alt: true, shift: true },
  expandDeck: { key: "f", alt: true, shift: true },
  settings: { key: ",", mod: true },
} satisfies Record<string, Shortcut>;

export type ShortcutName = keyof typeof shortcuts;
const mac = () => /Mac|iPhone|iPad/.test(navigator.platform);

export function shortcutKeys(name: ShortcutName): string {
  const shortcut: Shortcut = shortcuts[name];
  return [
    shortcut.mod ? (mac() ? "Meta" : "Control") : "",
    shortcut.alt ? "Alt" : "",
    shortcut.shift ? "Shift" : "",
    shortcut.key.toUpperCase(),
  ]
    .filter(Boolean)
    .join("+");
}

export function shortcutTitle(label: string, name: ShortcutName): string {
  return `${label} · ${shortcutKeys(name).replace("Meta", "⌘").replace("Control", "Ctrl")}`;
}

export function matchesShortcut(event: KeyboardEvent, name: ShortcutName): boolean {
  const shortcut: Shortcut = shortcuts[name];
  if (
    event.defaultPrevented ||
    event.repeat ||
    event.isComposing ||
    event.getModifierState("AltGraph")
  ) {
    return false;
  }
  // Never navigate away or operate a hidden workspace while a modal owns focus.
  if (event.composedPath().some((node) => node instanceof HTMLDialogElement && node.open)) {
    return false;
  }
  const keyMatches =
    event.key.toLowerCase() === shortcut.key || event.code === `Key${shortcut.key.toUpperCase()}`;
  return (
    keyMatches &&
    event.altKey === !!shortcut.alt &&
    event.shiftKey === !!shortcut.shift &&
    event.ctrlKey === (!!shortcut.mod && !mac()) &&
    event.metaKey === (!!shortcut.mod && mac())
  );
}

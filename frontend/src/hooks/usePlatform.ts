import { useMemo } from "react";

export type PlatformShortcutKey =
  | "mod"
  | "shift"
  | "alt"
  | "enter"
  | "escape"
  | string;

type PlatformType = "mac" | "windows" | "other";

type ShortcutCipher = {
  mod: string;
  shift: string;
  alt: string;
  enter: string;
  escape: string;
};

const MAC_CIPHER: ShortcutCipher = {
  mod: "⌘",
  shift: "⇧",
  alt: "⌥",
  enter: "↵",
  escape: "⎋",
};

const WINDOWS_CIPHER: ShortcutCipher = {
  mod: "Ctrl",
  shift: "Shift",
  alt: "Alt",
  enter: "Enter",
  escape: "Esc",
};

const detectPlatform = (): PlatformType => {
  if (typeof navigator === "undefined") {
    return "other";
  }

  const navigatorWithUAData = navigator as Navigator & {
    userAgentData?: { platform?: string };
  };

  const platform =
    navigatorWithUAData.userAgentData?.platform ??
    navigator.platform ??
    navigator.userAgent;

  if (/Mac|iPhone|iPad|iPod/i.test(platform)) {
    return "mac";
  }

  if (/Win/i.test(platform)) {
    return "windows";
  }

  return "other";
};

const getShortcutCipher = (platform: PlatformType): ShortcutCipher => {
  if (platform === "mac") {
    return MAC_CIPHER;
  }

  return WINDOWS_CIPHER;
};

const normalizeShortcutKey = (key: PlatformShortcutKey) =>
  key.toLocaleLowerCase();

const formatShortcutKeyWithCipher = (
  key: PlatformShortcutKey,
  shortcutCipher: ShortcutCipher,
) => {
  const normalizedKey = normalizeShortcutKey(key);

  if (normalizedKey === "mod") {
    return shortcutCipher.mod;
  }

  if (normalizedKey === "shift") {
    return shortcutCipher.shift;
  }

  if (normalizedKey === "alt") {
    return shortcutCipher.alt;
  }

  if (normalizedKey === "enter") {
    return shortcutCipher.enter;
  }

  if (normalizedKey === "escape") {
    return shortcutCipher.escape;
  }

  if (key.length === 1) {
    return key.toLocaleUpperCase();
  }

  return key;
};

export const usePlatform = () => {
  const platform = useMemo(detectPlatform, []);
  const shortcutCipher = useMemo(() => getShortcutCipher(platform), [platform]);

  const formatShortcutKey = (key: PlatformShortcutKey) =>
    formatShortcutKeyWithCipher(key, shortcutCipher);

  return {
    platform,
    isMac: platform === "mac",
    isWindows: platform === "windows",
    shortcutCipher,
    formatShortcutKey,
  };
};

import { useCallback, useEffect, useState, type KeyboardEvent } from "react";

type KeyboardShortcut = {
  key?: string;
  code?: string;
  ctrlOrMeta?: boolean;
  ctrlKey?: boolean;
  metaKey?: boolean;
  shiftKey?: boolean;
  altKey?: boolean;
  enabled?: boolean;
  preventDefault?: boolean;
  ignoreInEditable?: boolean;
};

const normalizeKey = (key: string) => key.toLocaleLowerCase();

const isEditableTarget = (target: EventTarget | null) => {
  if (!(target instanceof HTMLElement)) {
    return false;
  }

  if (target.isContentEditable) {
    return true;
  }

  const tagName = target.tagName;
  return tagName === "INPUT" || tagName === "TEXTAREA" || tagName === "SELECT";
};

export const useKeyboardShortcut = (
  {
    key,
    code,
    ctrlOrMeta,
    ctrlKey,
    metaKey,
    shiftKey,
    altKey,
    enabled = true,
    preventDefault = true,
    ignoreInEditable = false,
  }: KeyboardShortcut,
  callback: (event: globalThis.KeyboardEvent) => void,
) => {
  useEffect(() => {
    if (!enabled) {
      return;
    }

    const handleKeyDown = (event: globalThis.KeyboardEvent) => {
      if (ignoreInEditable && isEditableTarget(event.target)) {
        return;
      }

      if (ctrlOrMeta && !(event.ctrlKey || event.metaKey)) {
        return;
      }

      if (ctrlKey !== undefined && event.ctrlKey !== ctrlKey) {
        return;
      }

      if (metaKey !== undefined && event.metaKey !== metaKey) {
        return;
      }

      if (shiftKey !== undefined && event.shiftKey !== shiftKey) {
        return;
      }

      if (altKey !== undefined && event.altKey !== altKey) {
        return;
      }

      if (key && normalizeKey(event.key) !== normalizeKey(key)) {
        return;
      }

      if (code && event.code !== code) {
        return;
      }

      if (preventDefault) {
        event.preventDefault();
      }

      callback(event);
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [
    altKey,
    callback,
    code,
    ctrlKey,
    ctrlOrMeta,
    enabled,
    ignoreInEditable,
    key,
    metaKey,
    preventDefault,
    shiftKey,
  ]);
};

type UseListKeyboardNavigationOptions<T> = {
  items: T[];
  open: boolean;
  onConfirm: (item: T) => void;
  getInitialIndex?: () => number;
  global?: boolean;
};

export const useListKeyboardNavigation = <
  T,
  TElement extends HTMLElement = HTMLElement,
>({
  items,
  open,
  onConfirm,
  getInitialIndex,
  global = false,
}: UseListKeyboardNavigationOptions<T>) => {
  const [highlightedIndex, setHighlightedIndex] = useState(-1);

  useEffect(() => {
    if (!open) {
      return;
    }

    const rawInitialIndex =
      items.length === 0 ? -1 : (getInitialIndex?.() ?? 0);
    const nextIndex =
      rawInitialIndex < 0
        ? -1
        : rawInitialIndex < items.length
          ? rawInitialIndex
          : 0;

    const frameId = requestAnimationFrame(() => {
      setHighlightedIndex(items.length === 0 ? -1 : nextIndex);
    });

    return () => {
      cancelAnimationFrame(frameId);
    };
  }, [getInitialIndex, items, open]);

  const handleNavigationKey = useCallback(
    (key: string, isComposing: boolean, preventDefault: () => void) => {
      if (isComposing || items.length === 0) {
        return;
      }

      if (key === "ArrowDown") {
        preventDefault();
        setHighlightedIndex((previous) =>
          previous < 0 ? 0 : (previous + 1) % items.length,
        );
        return;
      }

      if (key === "ArrowUp") {
        preventDefault();
        setHighlightedIndex((previous) =>
          previous < 0
            ? items.length - 1
            : (previous - 1 + items.length) % items.length,
        );
        return;
      }

      if (key === "Enter") {
        preventDefault();
        const selectedItem = items[highlightedIndex];
        if (selectedItem) {
          onConfirm(selectedItem);
        }
      }
    },
    [highlightedIndex, items, onConfirm],
  );

  const onKeyDown = useCallback(
    (event: KeyboardEvent<TElement>) => {
      handleNavigationKey(event.key, event.nativeEvent.isComposing, () =>
        event.preventDefault(),
      );
    },
    [handleNavigationKey],
  );

  useEffect(() => {
    if (!global || !open) {
      return;
    }

    const handleGlobalKeyDown = (event: globalThis.KeyboardEvent) => {
      if (isEditableTarget(event.target)) {
        return;
      }

      handleNavigationKey(event.key, event.isComposing, () =>
        event.preventDefault(),
      );
    };

    window.addEventListener("keydown", handleGlobalKeyDown);
    return () => {
      window.removeEventListener("keydown", handleGlobalKeyDown);
    };
  }, [global, handleNavigationKey, open]);

  return {
    highlightedIndex,
    setHighlightedIndex,
    onKeyDown,
  };
};

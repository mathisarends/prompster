import { useCallback, useEffect, useRef, useState } from "react";

type UseBufferedControlledValueOptions<T> = {
  value: T;
  onChange: (value: T) => void;
  delayMs: number;
  isEqual?: (left: T, right: T) => boolean;
  onExternalValueChange?: (value: T) => void;
};

export function useBufferedControlledValue<T>({
  value,
  onChange,
  delayMs,
  isEqual = Object.is,
  onExternalValueChange,
}: UseBufferedControlledValueOptions<T>) {
  const bufferedValueRef = useRef(value);
  const lastValuePropRef = useRef(value);
  const syncTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [bufferedValue, setBufferedValueState] = useState(value);

  const cancelBufferedSync = useCallback(() => {
    if (syncTimeoutRef.current === null) return;

    clearTimeout(syncTimeoutRef.current);
    syncTimeoutRef.current = null;
  }, []);

  const replaceBufferedValue = useCallback(
    (nextValue: T) => {
      cancelBufferedSync();
      bufferedValueRef.current = nextValue;
      setBufferedValueState(nextValue);
    },
    [cancelBufferedSync],
  );

  const flushBufferedValue = useCallback(
    (nextValue = bufferedValueRef.current) => {
      cancelBufferedSync();
      onChange(nextValue);
    },
    [cancelBufferedSync, onChange],
  );

  const setBufferedValue = useCallback(
    (nextValue: T) => {
      bufferedValueRef.current = nextValue;
      setBufferedValueState(nextValue);

      cancelBufferedSync();
      syncTimeoutRef.current = setTimeout(() => {
        syncTimeoutRef.current = null;
        onChange(nextValue);
      }, delayMs);
    },
    [cancelBufferedSync, delayMs, onChange],
  );

  useEffect(() => {
    if (isEqual(value, lastValuePropRef.current)) return;

    lastValuePropRef.current = value;
    if (isEqual(value, bufferedValueRef.current)) return;

    replaceBufferedValue(value);
    onExternalValueChange?.(value);
  }, [isEqual, onExternalValueChange, replaceBufferedValue, value]);

  useEffect(() => cancelBufferedSync, [cancelBufferedSync]);

  return {
    bufferedValue,
    cancelBufferedSync,
    flushBufferedValue,
    replaceBufferedValue,
    setBufferedValue,
  };
}

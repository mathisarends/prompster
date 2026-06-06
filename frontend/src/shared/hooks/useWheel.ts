import { useCallback, type WheelEvent } from "react";

type UseWheelOptions = {
  disabled?: boolean;
  max?: number;
  min?: number;
  onChange: (value: number) => void;
  step?: number;
  value: number;
};

const clamp = (value: number, min: number, max: number) =>
  Math.min(max, Math.max(min, value));

export const useWheel = ({
  disabled = false,
  max = 100,
  min = 0,
  onChange,
  step = 4,
  value,
}: UseWheelOptions) =>
  useCallback(
    (event: WheelEvent<HTMLElement>) => {
      if (disabled) {
        return;
      }

      event.preventDefault();

      const wheelDelta = event.deltaY === 0 ? event.deltaX : event.deltaY;
      const direction = wheelDelta > 0 ? -1 : 1;
      const nextValue = clamp(value + direction * step, min, max);

      if (nextValue !== value) {
        onChange(nextValue);
      }
    },
    [disabled, max, min, onChange, step, value],
  );

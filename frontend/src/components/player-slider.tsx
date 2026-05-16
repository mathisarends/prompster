import {
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type ComponentProps,
} from "react";

import { cn } from "@/lib/utils";

type PlayerSliderProps = Omit<ComponentProps<"input">, "type"> & {
  value: number;
  max: number;
  showTooltip?: boolean;
  formatTooltip?: (value: number) => string;
};

export const PlayerSlider = ({
  value,
  max,
  min = 0,
  showTooltip = false,
  formatTooltip,
  className,
  style,
  onMouseMove,
  onMouseEnter,
  onMouseLeave,
  onBlur,
  ...props
}: PlayerSliderProps) => {
  const sliderRef = useRef<HTMLInputElement | null>(null);
  const [hoverPercent, setHoverPercent] = useState<number | null>(null);

  const numericMin = Number(min);
  const numericMax = Number(max);
  const valueRange = numericMax - numericMin;
  const numericValue = Number(value);
  const progress =
    valueRange > 0 ? ((numericValue - numericMin) / valueRange) * 100 : 0;
  const hasHoverPreview = hoverPercent !== null && !props.disabled;

  const hoverValue = useMemo(() => {
    if (hoverPercent === null || valueRange <= 0) {
      return numericValue;
    }

    return numericMin + (hoverPercent / 100) * valueRange;
  }, [hoverPercent, numericMin, numericValue, valueRange]);

  const tooltipValue = Math.round(hoverValue * 100) / 100;
  const defaultTooltipText = Number.isInteger(tooltipValue)
    ? String(tooltipValue)
    : tooltipValue.toFixed(2);

  const tooltipText = formatTooltip
    ? formatTooltip(tooltipValue)
    : defaultTooltipText;

  const previewStart = Math.min(progress, hoverPercent ?? progress);
  const previewWidth = Math.max(
    0,
    Math.abs(progress - (hoverPercent ?? progress)),
  );

  const updateHoverPercent = (clientX: number) => {
    const input = sliderRef.current;

    if (!input) {
      return;
    }

    const rect = input.getBoundingClientRect();
    if (rect.width <= 0) {
      return;
    }

    const nextPercent = ((clientX - rect.left) / rect.width) * 100;
    setHoverPercent(Math.min(100, Math.max(0, nextPercent)));
  };

  const sliderStyle = {
    "--player-slider-progress": `${Math.min(100, Math.max(0, progress))}%`,
    ...style,
  } as CSSProperties;

  return (
    <div className="player-slider-shell">
      {hasHoverPreview ? (
        <span
          aria-hidden
          className="player-slider-preview"
          style={
            {
              "--player-slider-preview-start": `${previewStart}%`,
              "--player-slider-preview-width": `${previewWidth}%`,
            } as CSSProperties
          }
        />
      ) : null}

      {showTooltip && hasHoverPreview ? (
        <span
          aria-hidden
          className="player-slider-tooltip"
          style={{ left: `${hoverPercent}%` }}
        >
          {tooltipText}
        </span>
      ) : null}

      <input
        ref={sliderRef}
        type="range"
        min={min}
        max={max}
        value={value}
        className={cn("player-slider", className)}
        style={sliderStyle}
        onMouseEnter={(event) => {
          updateHoverPercent(event.clientX);
          onMouseEnter?.(event);
        }}
        onMouseMove={(event) => {
          updateHoverPercent(event.clientX);
          onMouseMove?.(event);
        }}
        onMouseLeave={(event) => {
          setHoverPercent(null);
          onMouseLeave?.(event);
        }}
        onBlur={(event) => {
          setHoverPercent(null);
          onBlur?.(event);
        }}
        {...props}
      />
    </div>
  );
};

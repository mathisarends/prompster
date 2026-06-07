import { useEffect, useRef } from "react";

import { cn } from "@/shared/lib/utils";

const BAR_COUNT = 56;
const MIN_SCALE = 0.06;
// Voice energy sits in the lower frequency range, so only the lower portion of
// the FFT bins is mapped onto the bars to keep the motion lively and centered.
const USABLE_BIN_RATIO = 0.65;
// Higher value follows the audio faster; lower value smooths the motion.
const SMOOTHING = 0.4;

type TranscriptionWaveformProps = {
  analyser: AnalyserNode | null;
  active: boolean;
  className?: string;
};

export const TranscriptionWaveform = ({
  analyser,
  active,
  className,
}: TranscriptionWaveformProps) => {
  const barsRef = useRef<(HTMLSpanElement | null)[]>([]);

  useEffect(() => {
    const bars = barsRef.current;

    const resetBars = () => {
      bars.forEach((bar) => {
        if (bar) bar.style.transform = `scaleY(${MIN_SCALE})`;
      });
    };

    if (!analyser || !active) {
      resetBars();
      return;
    }

    const data = new Uint8Array(analyser.frequencyBinCount);
    const smoothed = new Array<number>(BAR_COUNT).fill(MIN_SCALE);
    const usableBins = Math.floor(analyser.frequencyBinCount * USABLE_BIN_RATIO);
    const binsPerBar = Math.max(1, Math.floor(usableBins / BAR_COUNT));

    let frame = 0;

    const render = () => {
      analyser.getByteFrequencyData(data);

      for (let index = 0; index < BAR_COUNT; index += 1) {
        let sum = 0;
        for (let offset = 0; offset < binsPerBar; offset += 1) {
          sum += data[index * binsPerBar + offset] ?? 0;
        }

        const average = sum / binsPerBar / 255;
        const target = MIN_SCALE + average * (1 - MIN_SCALE);
        smoothed[index] += (target - smoothed[index]) * SMOOTHING;

        const bar = bars[index];
        if (bar) bar.style.transform = `scaleY(${smoothed[index]})`;
      }

      frame = requestAnimationFrame(render);
    };

    frame = requestAnimationFrame(render);
    return () => cancelAnimationFrame(frame);
  }, [analyser, active]);

  return (
    <div
      aria-hidden
      className={cn(
        "flex h-8 w-full items-center justify-between gap-px",
        className,
      )}
    >
      {Array.from({ length: BAR_COUNT }).map((_, index) => (
        <span
          key={index}
          ref={(element) => {
            barsRef.current[index] = element;
          }}
          className="h-full w-0.5 flex-1 origin-center rounded-full bg-foreground/70"
          style={{ transform: `scaleY(${MIN_SCALE})` }}
        />
      ))}
    </div>
  );
};

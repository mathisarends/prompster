import { useEffect, useRef, useState } from "react";

type UseSmoothStreamingTextOptions = {
  isStreaming: boolean;
};

// Reveal pace, in characters per second. We keep a gentle floor so even tiny
// bursts animate visibly, and let the pace scale with how far behind we are so
// the displayed text never lags noticeably behind what the server has sent.
const MIN_CHARS_PER_SECOND = 90;
const MAX_CHARS_PER_SECOND = 1000;
const BACKLOG_SPEEDUP = 9;

const computeRevealSpeed = (backlog: number) =>
  Math.min(
    MAX_CHARS_PER_SECOND,
    Math.max(MIN_CHARS_PER_SECOND, backlog * BACKLOG_SPEEDUP),
  );

/**
 * Decouples the text the server has streamed in from the text shown on screen.
 *
 * Network chunks arrive in irregular bursts; rendering them verbatim makes the
 * message appear in jerky jumps and the trailing caret stutter. Instead we keep
 * a steady, framerate-independent reveal that smoothly catches up to the latest
 * received text. When streaming ends we snap to the full text so nothing is left
 * hidden (the final message may also differ slightly from the streamed chunks).
 */
export const useSmoothStreamingText = (
  fullText: string,
  { isStreaming }: UseSmoothStreamingTextOptions,
) => {
  const [displayedLength, setDisplayedLength] = useState(
    isStreaming ? 0 : fullText.length,
  );

  const fullTextRef = useRef(fullText);
  const frameRef = useRef<number | null>(null);
  const lastFrameTimeRef = useRef<number | null>(null);

  useEffect(() => {
    fullTextRef.current = fullText;
  }, [fullText]);

  useEffect(() => {
    if (!isStreaming) {
      if (frameRef.current !== null) {
        cancelAnimationFrame(frameRef.current);
        frameRef.current = null;
      }
      lastFrameTimeRef.current = null;
      setDisplayedLength(fullTextRef.current.length);
      return;
    }

    const tick = (now: number) => {
      const previous = lastFrameTimeRef.current ?? now;
      const deltaSeconds = (now - previous) / 1000;
      lastFrameTimeRef.current = now;

      setDisplayedLength((current) => {
        const target = fullTextRef.current.length;
        if (current >= target) return current;

        const backlog = target - current;
        const advance = Math.max(1, computeRevealSpeed(backlog) * deltaSeconds);
        return Math.min(target, Math.floor(current + advance));
      });

      frameRef.current = requestAnimationFrame(tick);
    };

    frameRef.current = requestAnimationFrame(tick);

    return () => {
      if (frameRef.current !== null) {
        cancelAnimationFrame(frameRef.current);
        frameRef.current = null;
      }
      lastFrameTimeRef.current = null;
    };
  }, [isStreaming]);

  // Guard against the target shrinking (e.g. a new message reusing this hook).
  const safeLength = Math.min(displayedLength, fullText.length);
  return fullText.slice(0, safeLength);
};

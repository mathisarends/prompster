import { useCallback, useEffect, useRef, useState, type RefObject } from "react";

const BOTTOM_THRESHOLD_PX = 48;

const getDistanceFromBottom = (element: HTMLElement) =>
  element.scrollHeight - element.scrollTop - element.clientHeight;

export const useStickyScroll = <T extends HTMLElement>(
  viewportRef: RefObject<T | null>,
  dependency: unknown,
) => {
  const [isAtBottom, setIsAtBottom] = useState(true);
  const stickToBottomRef = useRef(true);

  useEffect(() => {
    const viewport = viewportRef.current;
    if (!viewport) return;

    const handleScroll = () => {
      const atBottom = getDistanceFromBottom(viewport) <= BOTTOM_THRESHOLD_PX;
      stickToBottomRef.current = atBottom;
      setIsAtBottom(atBottom);
    };

    handleScroll();
    viewport.addEventListener("scroll", handleScroll, { passive: true });
    return () => viewport.removeEventListener("scroll", handleScroll);
  }, [viewportRef]);

  useEffect(() => {
    if (!stickToBottomRef.current) return;
    const viewport = viewportRef.current;
    if (!viewport) return;
    viewport.scrollTop = viewport.scrollHeight;
  }, [dependency, viewportRef]);

  const scrollToBottom = useCallback(
    (behavior: ScrollBehavior = "smooth") => {
      const viewport = viewportRef.current;
      if (!viewport) return;
      stickToBottomRef.current = true;
      viewport.scrollTo({ top: viewport.scrollHeight, behavior });
    },
    [viewportRef],
  );

  return { isAtBottom, scrollToBottom };
};

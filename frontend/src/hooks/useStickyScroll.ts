import { useCallback, useEffect, useRef, useState, type RefObject } from "react";

const BOTTOM_THRESHOLD_PX = 48;

const getDistanceFromBottom = (element: HTMLElement) =>
  element.scrollHeight - element.scrollTop - element.clientHeight;

export const useStickyScroll = <T extends HTMLElement>(
  viewportRef: RefObject<T | null>,
  dependency: unknown,
) => {
  const [isAtBottom, setIsAtBottom] = useState(true);
  const [showScrollToBottomButton, setShowScrollToBottomButton] =
    useState(false);
  const stickToBottomRef = useRef(true);

  useEffect(() => {
    const viewport = viewportRef.current;
    if (!viewport) return;

    const syncScrollState = () => {
      const distanceFromBottom = getDistanceFromBottom(viewport);
      const atBottom = distanceFromBottom <= BOTTOM_THRESHOLD_PX;
      stickToBottomRef.current = atBottom;
      setIsAtBottom(atBottom);
      setShowScrollToBottomButton(!atBottom);
    };

    syncScrollState();
    viewport.addEventListener("scroll", syncScrollState, { passive: true });

    const resizeObserver = new ResizeObserver(() => {
      syncScrollState();
    });
    resizeObserver.observe(viewport);

    return () => {
      viewport.removeEventListener("scroll", syncScrollState);
      resizeObserver.disconnect();
    };
  }, [viewportRef]);

  useEffect(() => {
    const viewport = viewportRef.current;
    if (!viewport) return;

    if (stickToBottomRef.current) {
      viewport.scrollTop = viewport.scrollHeight;
      return;
    }

    const distanceFromBottom = getDistanceFromBottom(viewport);
    const atBottom = distanceFromBottom <= BOTTOM_THRESHOLD_PX;
    setIsAtBottom(atBottom);
    setShowScrollToBottomButton(!atBottom);
  }, [dependency, viewportRef]);

  const scrollToBottom = useCallback(
    (behavior: ScrollBehavior = "smooth") => {
      const viewport = viewportRef.current;
      if (!viewport) return;
      stickToBottomRef.current = true;
      setShowScrollToBottomButton(false);
      viewport.scrollTo({ top: viewport.scrollHeight, behavior });
    },
    [viewportRef],
  );

  return { isAtBottom, showScrollToBottomButton, scrollToBottom };
};

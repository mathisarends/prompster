import { useCallback, useEffect, useState, type RefObject } from "react";

const BOTTOM_THRESHOLD_PX = 48;

const getDistanceFromBottom = (element: HTMLElement) =>
  element.scrollHeight - element.scrollTop - element.clientHeight;

export const useStickyScroll = <T extends HTMLElement>(
  viewportRef: RefObject<T | null>,
) => {
  const [isAtBottom, setIsAtBottom] = useState(true);
  const [showScrollToBottomButton, setShowScrollToBottomButton] =
    useState(false);

  useEffect(() => {
    const viewport = viewportRef.current;
    if (!viewport) return;

    const syncScrollState = () => {
      const distanceFromBottom = getDistanceFromBottom(viewport);
      const atBottom = distanceFromBottom <= BOTTOM_THRESHOLD_PX;
      setIsAtBottom(atBottom);
      setShowScrollToBottomButton(!atBottom);
    };

    syncScrollState();
    viewport.addEventListener("scroll", syncScrollState, { passive: true });

    const resizeObserver = new ResizeObserver(syncScrollState);
    resizeObserver.observe(viewport);
    if (viewport.firstElementChild) {
      resizeObserver.observe(viewport.firstElementChild);
    }

    return () => {
      viewport.removeEventListener("scroll", syncScrollState);
      resizeObserver.disconnect();
    };
  }, [viewportRef]);

  const scrollToBottom = useCallback(
    (behavior: ScrollBehavior = "smooth") => {
      const viewport = viewportRef.current;
      if (!viewport) return;
      setShowScrollToBottomButton(false);
      viewport.scrollTo({ top: viewport.scrollHeight, behavior });
    },
    [viewportRef],
  );

  return { isAtBottom, showScrollToBottomButton, scrollToBottom };
};

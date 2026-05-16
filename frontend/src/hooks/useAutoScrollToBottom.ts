import { useEffect, useRef } from "react";

export const useAutoScrollToBottom = <T extends HTMLElement>(
  dependency: unknown,
) => {
  const endRef = useRef<T>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [dependency]);

  return endRef;
};

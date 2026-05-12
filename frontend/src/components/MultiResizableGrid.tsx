import { useEffect, useRef, useState, type ReactNode } from "react";

type MultiResizableGridProps = {
  left: ReactNode;
  right: ReactNode;
  initialLeftWidth?: number;
  minLeftWidth?: number;
  maxLeftWidth?: number;
  className?: string;
  leftClassName?: string;
  rightClassName?: string;
};

const clamp = (value: number, min: number, max: number) =>
  Math.min(Math.max(value, min), max);

export const MultiResizableGrid = ({
  left,
  right,
  initialLeftWidth = 300,
  minLeftWidth = 250,
  maxLeftWidth = 520,
  className = "",
  leftClassName = "",
  rightClassName = "",
}: MultiResizableGridProps) => {
  const [leftWidth, setLeftWidth] = useState(initialLeftWidth);
  const dragState = useRef<{ startX: number; startWidth: number } | null>(null);

  useEffect(() => {
    const onPointerMove = (event: PointerEvent) => {
      if (!dragState.current) {
        return;
      }

      const delta = event.clientX - dragState.current.startX;
      const nextWidth = clamp(
        dragState.current.startWidth + delta,
        minLeftWidth,
        maxLeftWidth,
      );
      setLeftWidth(nextWidth);
    };

    const onPointerUp = () => {
      dragState.current = null;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };

    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", onPointerUp);

    return () => {
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", onPointerUp);
    };
  }, [maxLeftWidth, minLeftWidth]);

  const startDrag = (event: React.PointerEvent<HTMLDivElement>) => {
    dragState.current = { startX: event.clientX, startWidth: leftWidth };
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  };

  return (
    <div className={`h-full w-full overflow-hidden ${className}`}>
      <div className="h-full w-full lg:flex">
        <div
          className={`relative h-[42vh] w-full lg:h-full lg:shrink-0 ${leftClassName}`}
          style={{ width: `${leftWidth}px` }}
        >
          {left}
          <div
            aria-label="Resize sidebar"
            className="absolute right-0 top-0 hidden h-full w-2 cursor-col-resize transition-colors hover:bg-[var(--beatline-highlight)] lg:block"
            onPointerDown={startDrag}
            role="separator"
          />
        </div>

        <div className={`min-h-0 min-w-0 flex-1 ${rightClassName}`}>
          {right}
        </div>
      </div>
    </div>
  );
};

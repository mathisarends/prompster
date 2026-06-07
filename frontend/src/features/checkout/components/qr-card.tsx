import { Lock } from "lucide-react";

import { cn } from "@/shared/lib/utils";

type QrCardProps = {
  seed: number;
  year?: string;
  title?: string;
  artist?: string;
  lockedLabel?: string;
};

const qrCells = Array.from({ length: 49 }, (_, index) => index);

const isQrCellFilled = (cell: number, seed: number) => {
  const row = Math.floor(cell / 7);
  const col = cell % 7;
  const finder =
    (row < 2 && col < 2) || (row < 2 && col > 4) || (row > 4 && col < 2);

  return finder || (cell * 17 + seed * 11 + row * col) % 7 < 3;
};

export const QrCard = ({
  seed,
  year = "2008",
  title = "Haus am See",
  artist = "Peter Fox",
  lockedLabel,
}: QrCardProps) => {
  const isLocked = Boolean(lockedLabel);

  return (
    <article className="group min-h-[17.5rem] [perspective:1100px]">
      <div
        className={cn(
          "relative h-full min-h-[17.5rem] rounded-2xl transition duration-700 [transform-style:preserve-3d]",
          "group-hover:[transform:rotateY(180deg)] motion-reduce:transition-none motion-reduce:group-hover:[transform:none]",
          isLocked && "opacity-45 blur-[1px]",
        )}
      >
        <div
          className={cn(
            "absolute inset-0 overflow-hidden rounded-2xl border border-white/10 bg-[#0d1112] p-5 shadow-[0_22px_55px_hsl(0_0%_0%/0.28)] [backface-visibility:hidden]",
            isLocked && "border-white/[0.04]",
          )}
        >
          <span className="text-xs font-bold uppercase tracking-[0.18em] text-fuchsia-400">
            Scan
          </span>
          <div className="absolute inset-x-7 top-12 bottom-8 rounded-[50%] border border-fuchsia-500/45" />
          <div className="absolute inset-x-12 top-[4.45rem] bottom-14 rounded-[50%] border border-fuchsia-500/45" />
          <div className="absolute inset-x-[5.2rem] top-[7rem] bottom-[5.9rem] rounded-[50%] border border-fuchsia-500/45" />

          <div className="relative z-10 flex h-full min-h-[13.5rem] flex-col items-center justify-center gap-5">
            <div className="grid size-28 grid-cols-7 gap-1 rounded-xl bg-white p-5 shadow-[0_0_26px_hsl(0_0%_100%/0.12)]">
              {qrCells.map((cell) => (
                <span
                  key={cell}
                  className={cn(
                    "rounded-[1px]",
                    isQrCellFilled(cell, seed)
                      ? "bg-[#101416]"
                      : "bg-transparent",
                  )}
                />
              ))}
            </div>
            <p className="text-[0.66rem] font-semibold tracking-wide text-white/30">
              Scannen & abspielen
            </p>
          </div>
        </div>

        <div className="absolute inset-0 flex flex-col justify-between rounded-2xl border border-white/10 bg-[#151a1c] p-5 shadow-[0_22px_55px_hsl(0_0%_0%/0.28)] [backface-visibility:hidden] [transform:rotateY(180deg)]">
          <p className="text-xs font-black uppercase tracking-[0.2em] text-white/25">
            Prompster
          </p>

          <div>
            <p className="text-4xl font-black tracking-[-0.06em] text-emerald-300">
              {year}
            </p>
            <h3 className="mt-2 text-base font-black leading-tight text-white">
              {title}
            </h3>
            <p className="mt-1 text-sm font-semibold text-white/50">{artist}</p>
          </div>

          <p className="text-xs font-black uppercase tracking-[0.2em] text-white/25">
            Hoerjahr
          </p>
        </div>

        {isLocked ? (
          <div className="absolute inset-0 z-20 grid place-items-center rounded-2xl bg-[#080b0c]/35 backdrop-blur-sm">
            <div className="flex flex-col items-center gap-1 text-white/70">
              <Lock className="size-5" />
              <span className="text-sm font-semibold">{lockedLabel}</span>
            </div>
          </div>
        ) : null}
      </div>
    </article>
  );
};

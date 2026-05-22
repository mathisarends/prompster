import { LockKeyhole, Music2 } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

type SpotifyConnectDialogProps = {
  open: boolean;
  onConnect: () => void;
  isConnecting?: boolean;
};

export const SpotifyConnectDialog = ({
  open,
  onConnect,
  isConnecting = false,
}: SpotifyConnectDialogProps) => {
  return (
    <Dialog open={open} onOpenChange={() => undefined}>
      <DialogContent className="top-1/2 max-w-md -translate-y-1/2 rounded-2xl border-white/12 bg-[#121a14] p-0 text-white shadow-[0_28px_90px_rgb(0_0_0_/0.55)] backdrop-blur-xl">
        <div className="p-6 sm:p-7">
          <div className="mb-5 flex items-center gap-3">
            <div className="grid size-11 place-items-center rounded-xl bg-[#1db954]/16 text-[#1ed760]">
              <Music2 className="size-6" />
            </div>
            <div className="min-w-0">
              <DialogTitle className="text-2xl font-semibold tracking-normal text-white">
                Letzter Schritt!
              </DialogTitle>
              <DialogDescription className="mt-1 text-sm text-white/58">
                Spotify verbinden, dann geht es direkt los.
              </DialogDescription>
            </div>
          </div>

          <p className="text-base leading-7 text-white/78">
            Prompster braucht Zugriff auf deinen Spotify-Player, um die
            Hitster-Decks zu generieren.
          </p>

          <div className="mt-6 rounded-xl border border-white/10 bg-white/[0.04] p-4">
            <div className="flex items-start gap-3 text-sm text-white/64">
              <LockKeyhole className="mt-0.5 size-4 shrink-0 text-[#1ed760]" />
              <span>
                Die Verbindung wird nur für Player-Zugriff und passende
                Track-Vorschläge verwendet.
              </span>
            </div>
          </div>

          <Button
            type="button"
            onClick={onConnect}
            disabled={isConnecting}
            className="mt-6 h-11 w-full bg-[#1db954] text-[#07120b] hover:bg-[#1ed760]"
          >
            <Music2 className="size-4" />
            {isConnecting ? "Spotify verbindet..." : "Spotify verbinden"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

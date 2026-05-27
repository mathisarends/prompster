import { ExternalLink } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type OpenSpotifyPlaylistButtonProps = {
  url?: string;
  className?: string;
};

export const OpenSpotifyPlaylistButton = ({
  url,
  className,
}: OpenSpotifyPlaylistButtonProps) => (
  <Button
    type="button"
    size="sm"
    className={cn(
      "bg-emerald-500 text-emerald-950 shadow-[0_10px_24px_hsl(142_76%_36%/0.24)] hover:bg-emerald-400",
      className,
    )}
    disabled={!url}
    onClick={() => {
      if (url) window.open(url, "_blank", "noopener");
    }}
  >
    <ExternalLink className="size-4" />
    Öffnen
  </Button>
);

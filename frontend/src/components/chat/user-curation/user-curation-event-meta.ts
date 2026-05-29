import {
  Music2,
  Pin,
  PinOff,
  Plus,
  Trash2,
  type LucideIcon,
} from "lucide-react";

import {
  UserCurationEventTypeResponse,
  type UserCurationEventResponse,
} from "@/api/generated/model";

type UserCurationEventMeta = {
  label: string;
  restoreTooltip: string;
  Icon: LucideIcon;
  className: string;
};

export const userCurationEventMeta: Record<
  UserCurationEventResponse["eventType"],
  UserCurationEventMeta
> = {
  [UserCurationEventTypeResponse.track_added]: {
    label: "Hinzugefügt",
    restoreTooltip: "Änderungen rückgängig machen",
    Icon: Plus,
    className: "border-emerald-400/20 bg-emerald-400/10 text-emerald-200",
  },
  [UserCurationEventTypeResponse.track_removed]: {
    label: "Entfernt",
    restoreTooltip: "Track wiederherstellen",
    Icon: Trash2,
    className: "border-rose-400/20 bg-rose-400/10 text-rose-200",
  },
  [UserCurationEventTypeResponse.track_pinned]: {
    label: "Gepinnt",
    restoreTooltip: "Pin lösen",
    Icon: Pin,
    className: "border-amber-300/25 bg-amber-300/10 text-amber-100",
  },
  [UserCurationEventTypeResponse.track_unpinned]: {
    label: "Pin gelöst",
    restoreTooltip: "Erneut pinnen",
    Icon: PinOff,
    className: "border-sky-300/20 bg-sky-300/10 text-sky-100",
  },
};

export const UserCurationFallbackIcon = Music2;

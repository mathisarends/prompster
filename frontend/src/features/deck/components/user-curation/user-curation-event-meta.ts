import { Music2, Plus, Trash2, type LucideIcon } from "lucide-react";

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
};

export const UserCurationFallbackIcon = Music2;

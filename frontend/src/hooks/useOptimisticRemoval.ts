import { useState } from "react";
import { toast } from "sonner";

type UseOptimisticRemovalResult = {
  hiddenIds: Set<string>;
  loadingIds: Set<string>;
  removeTrack: (id: string) => void;
};

export function useOptimisticRemoval(
  onRemoveTrack?: (id: string) => Promise<void> | void,
): UseOptimisticRemovalResult {
  const [hiddenIds, setHiddenIds] = useState<Set<string>>(() => new Set());
  const [loadingIds, setLoadingIds] = useState<Set<string>>(() => new Set());

  const removeTrack = (id: string) => {
    if (!onRemoveTrack || loadingIds.has(id)) return;

    setLoadingIds((prev) => new Set(prev).add(id));
    setHiddenIds((prev) => new Set(prev).add(id));

    Promise.resolve(onRemoveTrack(id))
      .catch(() => {
        setHiddenIds((prev) => {
          const next = new Set(prev);
          next.delete(id);
          return next;
        });
        toast.error("Track konnte nicht aus der Playlist entfernt werden.");
      })
      .finally(() => {
        setLoadingIds((prev) => {
          const next = new Set(prev);
          next.delete(id);
          return next;
        });
      });
  };

  return { hiddenIds, loadingIds, removeTrack };
}

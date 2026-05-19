import { useState, type FormEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import type { SessionSummaryResponse } from "@/api/generated/model";
import {
  deleteSession,
  getListSessionsQueryKey,
  updateSession,
} from "@/api/generated/session-api";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";

const MAX_TITLE_LENGTH = 120;

type RenameChatDialogProps = {
  session: SessionSummaryResponse | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

export const RenameChatDialog = ({
  session,
  open,
  onOpenChange,
}: RenameChatDialogProps) => {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState("");
  const [trackedSessionId, setTrackedSessionId] = useState<string | null>(null);

  if (open && session && session.id !== trackedSessionId) {
    setTrackedSessionId(session.id);
    setTitle(session.title);
  }

  const mutation = useMutation({
    mutationFn: ({ id, nextTitle }: { id: string; nextTitle: string }) =>
      updateSession(id, { title: nextTitle }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: getListSessionsQueryKey(),
      });
      onOpenChange(false);
    },
  });

  const trimmed = title.trim();
  const canSave =
    Boolean(session) &&
    trimmed.length > 0 &&
    trimmed !== session?.title &&
    !mutation.isPending;

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (!session || !canSave) return;
    mutation.mutate({ id: session.id, nextTitle: trimmed });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md p-6">
        <DialogTitle className="text-lg">Chat umbenennen</DialogTitle>
        <DialogDescription className="mt-1.5 text-sm">
          Gib deinem Chat einen neuen Namen.
        </DialogDescription>
        <form className="mt-5 space-y-4" onSubmit={handleSubmit}>
          <Input
            autoFocus
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            maxLength={MAX_TITLE_LENGTH}
            placeholder="Chat-Titel"
          />
          {mutation.isError ? (
            <p className="text-sm text-destructive">
              Umbenennen fehlgeschlagen. Bitte erneut versuchen.
            </p>
          ) : null}
          <div className="flex justify-end gap-2">
            <Button
              type="button"
              variant="ghost"
              onClick={() => onOpenChange(false)}
              disabled={mutation.isPending}
            >
              Abbrechen
            </Button>
            <Button type="submit" disabled={!canSave}>
              {mutation.isPending ? "Speichern..." : "Speichern"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};

type DeleteChatDialogProps = {
  session: SessionSummaryResponse | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onDeleted?: (sessionId: string) => void;
};

export const DeleteChatDialog = ({
  session,
  open,
  onOpenChange,
  onDeleted,
}: DeleteChatDialogProps) => {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (id: string) => deleteSession(id),
    onSuccess: async (_data, id) => {
      await queryClient.invalidateQueries({
        queryKey: getListSessionsQueryKey(),
      });
      onOpenChange(false);
      onDeleted?.(id);
    },
  });

  const handleConfirm = () => {
    if (!session || mutation.isPending) return;
    mutation.mutate(session.id);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md p-6">
        <DialogTitle className="text-lg">Chat löschen?</DialogTitle>
        <DialogDescription className="mt-1.5 text-sm">
          {session
            ? `„${session.title}" wird endgültig gelöscht. Diese Aktion kann nicht rückgängig gemacht werden.`
            : "Diese Aktion kann nicht rückgängig gemacht werden."}
        </DialogDescription>
        {mutation.isError ? (
          <p className="mt-3 text-sm text-destructive">
            Löschen fehlgeschlagen. Bitte erneut versuchen.
          </p>
        ) : null}
        <div className="mt-6 flex justify-end gap-2">
          <Button
            type="button"
            variant="ghost"
            onClick={() => onOpenChange(false)}
            disabled={mutation.isPending}
          >
            Abbrechen
          </Button>
          <Button
            type="button"
            variant="destructive"
            onClick={handleConfirm}
            disabled={mutation.isPending}
          >
            {mutation.isPending ? "Löschen..." : "Löschen"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

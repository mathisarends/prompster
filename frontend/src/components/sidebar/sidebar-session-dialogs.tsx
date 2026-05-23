import { useState, type FormEvent, type ReactNode } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import type { SessionSummaryResponse } from "@/api/generated/model";
import {
  deleteSession,
  getGetSessionQueryKey,
  getListSessionsQueryKey,
  updateSession,
} from "@/api/generated/session-api";
import { deleteMe, useGetDeleteInformation } from "@/api/generated/user-api";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";

const MAX_TITLE_LENGTH = 120;

type ChatDialogSession = Pick<SessionSummaryResponse, "id" | "title">;

type RenameChatDialogProps = {
  session: ChatDialogSession | null;
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
    onSuccess: async (_data, { id }) => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: getListSessionsQueryKey(),
        }),
        queryClient.invalidateQueries({
          queryKey: getGetSessionQueryKey(id),
        }),
      ]);
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
      <DialogContent className="max-w-xl p-8">
        <DialogTitle className="text-2xl">Chat umbenennen</DialogTitle>
        <DialogDescription className="mt-0.5 text-base">
          Gib deinem Chat einen neuen Namen.
        </DialogDescription>
        <form className="mt-6 space-y-5" onSubmit={handleSubmit}>
          <Input
            autoFocus
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            maxLength={MAX_TITLE_LENGTH}
            placeholder="Chat-Titel"
            className="h-11 text-base"
          />
          {mutation.isError ? (
            <p className="text-sm text-destructive">
              Umbenennen fehlgeschlagen. Bitte erneut versuchen.
            </p>
          ) : null}
          <div className="flex justify-end gap-2">
            <Button
              type="button"
              size="lg"
              variant="ghost"
              onClick={() => onOpenChange(false)}
              disabled={mutation.isPending}
            >
              Abbrechen
            </Button>
            <Button type="submit" size="lg" disabled={!canSave}>
              {mutation.isPending ? "Speichern..." : "Speichern"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};

type DeleteChatDialogProps = {
  session: ChatDialogSession | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onDeleted?: (sessionId: string) => void;
};

type DeleteConfirmationDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: ReactNode;
  isPending: boolean;
  isError: boolean;
  errorMessage: string;
  confirmLabel: string;
  pendingConfirmLabel: string;
  onConfirm: () => void;
};

const DeleteConfirmationDialog = ({
  open,
  onOpenChange,
  title,
  description,
  isPending,
  isError,
  errorMessage,
  confirmLabel,
  pendingConfirmLabel,
  onConfirm,
}: DeleteConfirmationDialogProps) => (
  <Dialog open={open} onOpenChange={onOpenChange}>
    <DialogContent className="max-w-xl p-8">
      <DialogTitle className="text-2xl">{title}</DialogTitle>
      <DialogDescription className="mt-2 text-base">
        {description}
      </DialogDescription>
      {isError ? (
        <p className="mt-4 text-sm text-destructive">{errorMessage}</p>
      ) : null}
      <div className="mt-7 flex justify-end gap-2">
        <Button
          type="button"
          size="lg"
          variant="ghost"
          onClick={() => onOpenChange(false)}
          disabled={isPending}
        >
          Abbrechen
        </Button>
        <Button
          type="button"
          size="lg"
          variant="destructive"
          onClick={onConfirm}
          disabled={isPending}
        >
          {isPending ? pendingConfirmLabel : confirmLabel}
        </Button>
      </div>
    </DialogContent>
  </Dialog>
);

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
      toast.success("Chat gelöscht");
    },
  });

  const handleConfirm = () => {
    if (!session || mutation.isPending) return;
    mutation.mutate(session.id);
  };

  return (
    <DeleteConfirmationDialog
      open={open}
      onOpenChange={onOpenChange}
      title="Chat löschen?"
      description={
        session
          ? `„${session.title}" wird endgültig gelöscht. Diese Aktion kann nicht rückgängig gemacht werden.`
          : "Diese Aktion kann nicht rückgängig gemacht werden."
      }
      isPending={mutation.isPending}
      isError={mutation.isError}
      errorMessage="Löschen fehlgeschlagen. Bitte erneut versuchen."
      confirmLabel="Löschen"
      pendingConfirmLabel="Löschen..."
      onConfirm={handleConfirm}
    />
  );
};

type DeleteAccountDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onDeleted?: () => Promise<void> | void;
};

const getSessionCountLabel = (sessionCount: number) => {
  return sessionCount === 1
    ? "1 Session wird mit gelöscht."
    : `${sessionCount} Sessions werden mit gelöscht.`;
};

export const DeleteAccountDialog = ({
  open,
  onOpenChange,
  onDeleted,
}: DeleteAccountDialogProps) => {
  const deleteInformation = useGetDeleteInformation({
    query: { enabled: open },
  });

  const mutation = useMutation({
    mutationFn: () => deleteMe(),
    onSuccess: async () => {
      onOpenChange(false);
      await onDeleted?.();
      toast.success("Account gelöscht");
    },
  });

  const handleConfirm = () => {
    if (mutation.isPending) return;
    mutation.mutate();
  };

  const sessionCountMessage =
    typeof deleteInformation.data?.sessionCount === "number"
      ? getSessionCountLabel(deleteInformation.data.sessionCount)
      : deleteInformation.isLoading
        ? "Session-Anzahl wird geladen..."
        : "Deine Sessions werden ebenfalls dauerhaft gelöscht.";

  return (
    <DeleteConfirmationDialog
      open={open}
      onOpenChange={onOpenChange}
      title="Account löschen?"
      description={
        <>
          Dein Account wird dauerhaft gelöscht. Diese Aktion kann nicht
          rückgängig gemacht werden.
          <span className="mt-2 block font-medium">{sessionCountMessage}</span>
        </>
      }
      isPending={mutation.isPending}
      isError={mutation.isError}
      errorMessage="Account konnte nicht gelöscht werden. Bitte erneut versuchen."
      confirmLabel="Account löschen"
      pendingConfirmLabel="Account wird gelöscht..."
      onConfirm={handleConfirm}
    />
  );
};

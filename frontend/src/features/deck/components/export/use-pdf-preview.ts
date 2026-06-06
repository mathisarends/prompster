import { useCallback, useEffect, useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";

import type { PlaylistTrackResponse } from "@/api/generated/model";
import { exportSessionPlaylist } from "@/api/generated/session-api";

import type { PdfPreview } from "./types";

type UsePdfPreviewProps = {
  sessionId: string;
  tracks: PlaylistTrackResponse[];
};

export const usePdfPreview = ({ sessionId, tracks }: UsePdfPreviewProps) => {
  const [pdfPreview, setPdfPreview] = useState<PdfPreview | null>(null);

  const previewKey = useMemo(
    () =>
      tracks
        .map(
          (track) =>
            `${track.id}:${track.title}:${track.artist}:${track.year ?? ""}:${track.spotifyUri ?? ""}`,
        )
        .join("|"),
    [tracks],
  );

  const clearPdfPreview = useCallback(() => {
    setPdfPreview((currentPreview) => {
      if (currentPreview) {
        window.URL.revokeObjectURL(currentPreview.url);
      }

      return null;
    });
  }, []);

  const { mutate: generatePreview, isPending: isLoadingPdfPreview } =
    useMutation({
      mutationFn: () => exportSessionPlaylist(sessionId, { pages: 2 }),
      onSuccess: (data) => {
        const blob =
          data instanceof Blob
            ? data
            : new Blob([data as BlobPart], { type: "application/pdf" });
        const url = window.URL.createObjectURL(blob);

        setPdfPreview((currentPreview) => {
          if (currentPreview) {
            window.URL.revokeObjectURL(currentPreview.url);
          }

          return { url, blob };
        });
      },
      onError: () => {
        toast.error("PDF-Vorschau konnte nicht erstellt werden.");
      },
    });

  useEffect(() => {
    clearPdfPreview();
    if (tracks.length > 0) {
      generatePreview();
    }
  }, [clearPdfPreview, generatePreview, previewKey, sessionId, tracks.length]);

  useEffect(
    () => () => {
      clearPdfPreview();
    },
    [clearPdfPreview],
  );

  return {
    pdfPreview,
    isLoadingPdfPreview,
  };
};
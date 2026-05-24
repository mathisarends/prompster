import { useEffect, useRef, useState } from "react";
import { Download, FileText, Loader2, Music2 } from "lucide-react";

import { Button } from "@/components/ui/button";

import type { PdfPreview } from "./types";

type DeckExportActionsProps = {
  trackCount: number;
  pdfPreview: PdfPreview | null;
  isActive: boolean;
  isLoadingPdfPreview: boolean;
  isDownloadingPdf: boolean;
  isExportingSpotify: boolean;
  onDownloadPdf: () => void;
  onExportSpotify: () => void;
};

export const DeckExportActions = ({
  trackCount,
  pdfPreview,
  isActive,
  isLoadingPdfPreview,
  isDownloadingPdf,
  isExportingSpotify,
  onDownloadPdf,
  onExportSpotify,
}: DeckExportActionsProps) => {
  const disabled = trackCount === 0;
  const previewShellRef = useRef<HTMLDivElement>(null);
  const [previewWidth, setPreviewWidth] = useState(0);
  const [isPreviewVisible, setIsPreviewVisible] = useState(false);

  const pdfPreviewUrl = pdfPreview
    ? `${pdfPreview.url}#toolbar=0&navpanes=0&scrollbar=0&view=FitH`
    : null;
  const previewHeight = previewWidth > 0 ? Math.ceil(previewWidth * 2.86) : 0;
  const showPreviewLoader =
    isLoadingPdfPreview || (Boolean(pdfPreviewUrl) && !isPreviewVisible);

  useEffect(() => {
    const shell = previewShellRef.current;
    if (!shell) return;

    const updatePreviewWidth = () => {
      setPreviewWidth(shell.clientWidth);
    };

    const resizeObserver = new ResizeObserver(updatePreviewWidth);
    resizeObserver.observe(shell);
    updatePreviewWidth();

    return () => {
      resizeObserver.disconnect();
    };
  }, []);

  useEffect(() => {
    setIsPreviewVisible(false);
    if (!pdfPreviewUrl || !isActive) return;

    const timer = window.setTimeout(() => {
      setIsPreviewVisible(true);
    }, 180);

    return () => {
      window.clearTimeout(timer);
    };
  }, [pdfPreviewUrl, isActive]);

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden pt-1">
      <p className="mb-2 rounded-md border border-white/[0.08] bg-white/[0.035] px-3 py-2 text-[11px] leading-relaxed text-muted-foreground">
        Die PDF-Ansicht ist nur eine Vorschau (erste 2 Seiten). Das finale
        Karten-PDF nutzt denselben Look und dasselbe Layout fur alle Karten.
      </p>

      <div
        ref={previewShellRef}
        className="prompster-scrollbar relative min-h-0 flex-1 overflow-auto rounded-md border border-white/[0.08] bg-white/[0.025]"
      >
        {pdfPreviewUrl ? (
          <>
            <iframe
              src={pdfPreviewUrl}
              title="PDF-Vorschau"
              className="block w-full bg-white transition-opacity duration-150"
              style={{
                height: previewHeight ? `${previewHeight}px` : "720px",
                opacity: isPreviewVisible ? 1 : 0,
              }}
              scrolling="no"
              onLoad={() => {
                window.setTimeout(() => setIsPreviewVisible(true), 80);
              }}
            />
            {showPreviewLoader ? <PdfPreviewLoader /> : null}
          </>
        ) : (
          <PdfPreviewEmptyState isLoading={isLoadingPdfPreview} />
        )}
      </div>

      {disabled ? (
        <p className="px-1 py-3 text-xs text-muted-foreground">
          Fuge mindestens einen Song hinzu, um die Liste zu exportieren.
        </p>
      ) : null}

      <div className="deck-export-bar -mx-5 -mb-5 mt-3 shrink-0 border-t border-white/[0.08] bg-background/78 px-5 pb-3 pt-4 shadow-[0_-18px_46px_hsl(222_52%_4%/0.36)] backdrop-blur-xl">
        <div className="flex min-h-16 items-center gap-3 px-1.5">
          <div className="grid size-12 shrink-0 place-items-center rounded-[4px] bg-white/[0.06] text-primary shadow-[0_10px_28px_hsl(0_0%_0%/0.28)] ring-1 ring-white/[0.06]">
            <FileText className="size-5" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold leading-tight text-foreground">
              Karten-PDF
            </p>
            <p className="mt-0.5 truncate text-xs text-muted-foreground">
              {pdfPreview
                ? "Nur Vorschau: erste 2 Seiten"
                : "Vorschau wird geladen"}
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              aria-label="PDF herunterladen"
              disabled={disabled || isDownloadingPdf || isExportingSpotify}
              onClick={onDownloadPdf}
            >
              {isDownloadingPdf ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <Download className="size-4" />
              )}
              PDF herunterladen
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              aria-label="Spotify-Playlist erstellen"
              disabled={disabled || isDownloadingPdf || isExportingSpotify}
              onClick={onExportSpotify}
            >
              {isExportingSpotify ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <Music2 className="size-4" />
              )}
              Spotify exportieren
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

const PdfPreviewLoader = () => (
  <div className="absolute inset-0 z-10 grid place-items-center bg-background/92 px-6 text-center backdrop-blur-sm">
    <div className="max-w-xs">
      <div className="mx-auto grid size-14 place-items-center rounded-md bg-primary/12 text-primary">
        <Loader2 className="size-6 animate-spin" />
      </div>
      <p className="mt-4 text-sm font-semibold">PDF-Vorschau wird geladen</p>
      <p className="mt-1 text-xs leading-5 text-muted-foreground">
        Vorschau mit den ersten zwei Seiten. Das finale PDF nutzt denselben
        Karten-Look fur alle Seiten.
      </p>
    </div>
  </div>
);

const PdfPreviewEmptyState = ({ isLoading }: { isLoading: boolean }) => (
  <div className="grid h-full min-h-[360px] place-items-center px-6 text-center">
    <div className="max-w-xs">
      <div className="mx-auto grid size-14 place-items-center rounded-md bg-primary/12 text-primary">
        {isLoading ? (
          <Loader2 className="size-6 animate-spin" />
        ) : (
          <FileText className="size-6" />
        )}
      </div>
      <p className="mt-4 text-sm font-semibold">PDF-Vorschau wird erstellt</p>
      <p className="mt-1 text-xs leading-5 text-muted-foreground">
        Die Vorschau zeigt nur einen Auszug. Das finale PDF enthalt alle Karten
        im selben Layout.
      </p>
    </div>
  </div>
);
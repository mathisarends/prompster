import { Image, X } from "lucide-react";

import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogTitle,
} from "@/shared/ui/dialog";

import type { ChatAttachment } from "./attachment-types";

type ImageAttachmentPreviewDialogProps = {
  attachment: ChatAttachment;
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

export const ImageAttachmentPreviewDialog = ({
  attachment,
  open,
  onOpenChange,
}: ImageAttachmentPreviewDialogProps) => (
  <Dialog open={open} onOpenChange={onOpenChange}>
    <DialogContent
      backdropClassName="bg-black/74 backdrop-blur-[1px]"
      className="inset-0 left-0 top-0 flex h-dvh max-h-none w-screen max-w-none translate-x-0 flex-col rounded-none border-0 bg-transparent p-0 text-white shadow-none data-open:zoom-in-100 data-closed:zoom-out-100"
      onClick={() => onOpenChange(false)}
    >
      <div className="pointer-events-none fixed inset-x-0 top-0 z-10 flex h-16 items-center justify-end px-5">
        <DialogTitle className="sr-only">Bildvorschau</DialogTitle>
        <DialogClose
          className="pointer-events-auto grid size-10 place-items-center rounded-full text-white/85 outline-none transition hover:bg-white/10 hover:text-white focus-visible:ring-2 focus-visible:ring-white/70"
          aria-label="Vorschau schliessen"
        >
          <X className="size-5" />
        </DialogClose>
      </div>

      <div className="flex min-h-0 flex-1 items-center justify-center p-6 sm:p-10">
        {attachment.imageUrl ? (
          <img
            src={attachment.imageUrl}
            alt=""
            className="max-h-[calc(100dvh-5rem)] max-w-[calc(100vw-3rem)] object-contain"
            onClick={(event) => event.stopPropagation()}
          />
        ) : (
          <Image
            className="size-12 text-white/55"
            onClick={(event) => event.stopPropagation()}
          />
        )}
      </div>
    </DialogContent>
  </Dialog>
);

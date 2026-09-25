import { uploadImageAttachment } from "@/api/generated/image-attachments/image-attachments";
import type { ImageAttachmentReferenceRequest } from "@/api/session-rpc";
import type {
  UploadedImageAttachmentResponse,
} from "@/api/generated/model";

export const toImageAttachmentReference = (
  image: UploadedImageAttachmentResponse,
): ImageAttachmentReferenceRequest => ({
  id: image.id,
  storageKey: image.storageKey,
  contentType: image.contentType,
  fileName: image.fileName,
  sizeBytes: image.sizeBytes,
});

export const uploadImageFile = async (
  file: File,
  signal?: AbortSignal,
): Promise<ImageAttachmentReferenceRequest> => {
  const image = await uploadImageAttachment({ file }, undefined, signal);

  return toImageAttachmentReference(image);
};

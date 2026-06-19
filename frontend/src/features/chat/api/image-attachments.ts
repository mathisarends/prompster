import { uploadSessionImageAttachment } from "@/api/generated/session-api";
import type {
  ImageAttachmentReferenceRequest,
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

export const uploadSessionImageFile = async (
  sessionId: string,
  file: File,
  signal?: AbortSignal,
): Promise<ImageAttachmentReferenceRequest> => {
  const image = await uploadSessionImageAttachment(
    sessionId,
    { file },
    undefined,
    signal,
  );

  return toImageAttachmentReference(image);
};

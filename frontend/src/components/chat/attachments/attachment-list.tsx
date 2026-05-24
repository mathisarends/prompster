import { AttachmentChip } from "./attachment-chip";
import type { ChatAttachment } from "./attachment-types";

type AttachmentListProps = {
  attachments: ChatAttachment[];
  onRemove?: (attachment: ChatAttachment) => void;
};

export const AttachmentList = ({
  attachments,
  onRemove,
}: AttachmentListProps) => {
  if (attachments.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2 pb-2.5">
      {attachments.map((attachment) => (
        <AttachmentChip
          key={`${attachment.kind}:${attachment.id}`}
          attachment={attachment}
          onRemove={onRemove}
        />
      ))}
    </div>
  );
};

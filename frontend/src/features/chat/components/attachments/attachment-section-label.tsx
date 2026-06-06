type AttachmentSectionLabelProps = {
  label: string;
};

export const AttachmentSectionLabel = ({
  label,
}: AttachmentSectionLabelProps) => (
  <p className="px-2 pb-1 pt-2 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground/80">
    {label}
  </p>
);

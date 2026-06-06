import { AttachmentFilterPill } from "./attachment-filter-pill";

export type AttachmentResultFilter = "all" | "playlists" | "artists";

const filterOptions: { value: AttachmentResultFilter; label: string }[] = [
  { value: "all", label: "Alle" },
  { value: "playlists", label: "Playlists" },
  { value: "artists", label: "Artists" },
];

type AttachmentSearchFiltersProps = {
  value: AttachmentResultFilter;
  onChange: (value: AttachmentResultFilter) => void;
};

export const AttachmentSearchFilters = ({
  value,
  onChange,
}: AttachmentSearchFiltersProps) => (
  <div className="flex gap-1.5 border-b border-white/[0.06] px-3 py-2">
    {filterOptions.map((option) => (
      <AttachmentFilterPill
        key={option.value}
        value={option.value}
        label={option.label}
        isActive={value === option.value}
        onSelect={onChange}
      />
    ))}
  </div>
);

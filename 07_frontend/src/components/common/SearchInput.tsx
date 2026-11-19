import { useId } from "react";
import { Search, X } from "lucide-react";

export function SearchInput({
  value,
  onChange,
  placeholder,
  label = "Cari",
}: {
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
  label?: string;
}) {
  const inputId = useId();

  return (
    <div className="relative w-full">
      <label htmlFor={inputId} className="sr-only">
        {label}
      </label>
      <Search
        className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted"
        aria-hidden="true"
      />
      <input
        id={inputId}
        type="search"
        className="input pl-10 pr-10"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        autoComplete="off"
        aria-label={label}
      />
      {value !== "" && (
        <button
          type="button"
          onClick={() => onChange("")}
          className="absolute right-2 top-1/2 flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-lg text-muted hover:bg-surface-low hover:text-foreground"
          aria-label="Hapus pencarian"
        >
          <X className="h-4 w-4" aria-hidden="true" />
        </button>
      )}
    </div>
  );
}

import { ChevronLeft, ChevronRight } from "lucide-react";

export function Pagination({
  page,
  totalPages,
  onChange,
}: {
  page: number;
  totalPages: number;
  onChange: (page: number) => void;
}) {
  if (totalPages <= 1) {
    return null;
  }

  return (
    <nav
      className="flex flex-wrap items-center justify-between gap-3 pt-2"
      aria-label="Pagination"
    >
      <p className="text-xs font-medium text-muted">
        Halaman <span className="font-bold text-primary">{page}</span> dari{" "}
        {totalPages}
      </p>
      <div className="flex items-center gap-2">
        <button
          type="button"
          className="btn-secondary min-h-10 px-3 text-xs"
          onClick={() => onChange(Math.max(1, page - 1))}
          disabled={page <= 1}
        >
          <ChevronLeft className="h-4 w-4" aria-hidden="true" />
          Sebelumnya
        </button>
        <button
          type="button"
          className="btn-secondary min-h-10 px-3 text-xs"
          onClick={() => onChange(Math.min(totalPages, page + 1))}
          disabled={page >= totalPages}
        >
          Berikutnya
          <ChevronRight className="h-4 w-4" aria-hidden="true" />
        </button>
      </div>
    </nav>
  );
}

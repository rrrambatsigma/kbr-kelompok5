export function Spinner({
  label = "Memuat data",
  className = "",
}: {
  label?: string;
  className?: string;
}) {
  return (
    <span className={`inline-flex items-center gap-3 ${className}`} role="status">
      <span
        className="h-5 w-5 animate-spin rounded-full border-2 border-secondary border-t-transparent"
        aria-hidden="true"
      />
      <span className="text-sm text-muted">{label}</span>
    </span>
  );
}

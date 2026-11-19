import { Link } from "react-router-dom";

export function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <Link
      to="/"
      className="inline-flex items-center gap-3 rounded-xl focus-visible:ring-2"
      aria-label="TaniCare — Beranda"
    >
      <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-primary-container text-[#c4e19c] shadow-sm">
        <svg
          viewBox="0 0 24 24"
          className="h-6 w-6 fill-current"
          aria-hidden="true"
        >
          <path d="M17 8C8 10 5.9 16.17 3.82 21.34L5.71 22l1-2.3A4.49 4.49 0 0 0 8 20C19 20 22 3 22 3c-1 2-8 2.25-13 3.25S2 11.5 2 13.5s1.75 3.75 1.75 3.75C7 8 17 8 17 8z" />
        </svg>
      </span>
      <span className="flex flex-col leading-none">
        <span className="font-heading text-xl font-extrabold tracking-tight text-primary">
          TaniCare
        </span>
        {!compact && (
          <span className="mt-1 text-[11px] font-medium text-muted">
            Sistem Pakar Tanaman Pangan
          </span>
        )}
      </span>
    </Link>
  );
}

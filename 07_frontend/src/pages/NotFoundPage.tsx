import { ArrowLeft, Leaf } from "lucide-react";
import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <div className="container-page flex min-h-[60vh] flex-col items-center justify-center gap-4 py-16 text-center">
      <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-surface-low text-primary">
        <Leaf className="h-7 w-7" aria-hidden="true" />
      </span>
      <p className="font-mono text-xs font-semibold uppercase tracking-wider text-secondary">
        404
      </p>
      <h1 className="font-heading text-3xl font-extrabold text-primary">
        Halaman tidak ditemukan
      </h1>
      <p className="max-w-md text-sm leading-6 text-muted">
        Alamat yang Anda buka tidak tersedia. Kembali ke beranda atau mulai
        diagnosis tanaman.
      </p>
      <div className="flex flex-wrap justify-center gap-2">
        <Link to="/" className="btn-secondary">
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          Beranda
        </Link>
        <Link to="/diagnosis" className="btn-primary">
          Mulai Diagnosis
        </Link>
      </div>
    </div>
  );
}

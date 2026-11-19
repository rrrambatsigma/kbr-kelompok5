import { Link } from "react-router-dom";

import { Logo } from "../common/Logo";

export function Footer() {
  return (
    <footer className="no-print mt-auto border-t border-border bg-surface-low">
      <div className="container-page grid gap-8 py-12 md:grid-cols-12">
        <div className="space-y-3 md:col-span-6">
          <Logo />
          <p className="max-w-md text-sm leading-6 text-muted">
            Sistem pakar berbasis pengetahuan untuk membantu identifikasi
            kemungkinan penyakit tanaman pangan tropis secara terstruktur.
          </p>
        </div>
        <div className="md:col-span-3">
          <p className="font-heading text-sm font-bold text-foreground">
            Navigasi
          </p>
          <nav className="mt-3 flex flex-col gap-2 text-sm text-muted">
            <Link className="hover:text-primary" to="/">
              Beranda
            </Link>
            <Link className="hover:text-primary" to="/diagnosis">
              Diagnosis
            </Link>
            <Link className="hover:text-primary" to="/knowledge-base">
              Knowledge Base
            </Link>
          </nav>
        </div>
        <div className="md:col-span-3">
          <p className="font-heading text-sm font-bold text-foreground">
            Tentang Proyek
          </p>
          <p className="mt-3 text-sm leading-6 text-muted">
            Proyek Knowledge-Based Reasoning — Kelompok 5. Hasil diagnosis
            adalah informasi pendukung, bukan pengganti pemeriksaan ahli.
          </p>
        </div>
      </div>
      <div className="border-t border-border">
        <div className="container-page flex flex-col gap-2 py-5 text-xs text-muted sm:flex-row sm:items-center sm:justify-between">
          <p>© 2026 TaniCare — Sistem Pakar Penyakit Tanaman Pangan Tropis.</p>
          <p className="font-semibold text-secondary">
            Proyek Sistem Pakar • Kelompok 5
          </p>
        </div>
      </div>
    </footer>
  );
}

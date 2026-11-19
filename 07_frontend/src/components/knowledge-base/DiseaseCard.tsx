import { ArrowUpRight, Leaf } from "lucide-react";
import { Link } from "react-router-dom";

import type { DiseaseSummary } from "../../types/api";

export function DiseaseCard({ disease }: { disease: DiseaseSummary }) {
  return (
    <Link
      to={`/knowledge-base/${encodeURIComponent(disease.id)}`}
      className="card-interactive group flex flex-col gap-4 p-5"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex flex-wrap gap-1.5">
          <span className="badge-success">
            <Leaf className="h-3 w-3" aria-hidden="true" />
            {disease.plantLabel ?? disease.plantId ?? "Tanaman"}
          </span>
          <span className="badge-neutral">{disease.symptomCount} gejala</span>
        </div>
        <ArrowUpRight
          className="h-4 w-4 text-muted transition-colors group-hover:text-primary"
          aria-hidden="true"
        />
      </div>
      <div>
        <h3 className="font-heading text-base font-bold leading-6 text-foreground group-hover:text-primary">
          {disease.label}
        </h3>
        <p className="mt-2 text-xs leading-5 text-muted">
          Entri penyakit pada knowledge base TaniCare. Buka detail untuk melihat
          patogen, gejala, bagian terdampak, fase, dan pengendalian.
        </p>
      </div>
      <span className="mt-auto inline-flex items-center gap-1 text-xs font-semibold text-secondary group-hover:text-primary">
        Detail patologi
        <ArrowUpRight className="h-3.5 w-3.5" aria-hidden="true" />
      </span>
    </Link>
  );
}

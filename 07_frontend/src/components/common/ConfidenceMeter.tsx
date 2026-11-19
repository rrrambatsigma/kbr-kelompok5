import type { Confidence } from "../../types/api";
import {
  confidenceLabel,
  confidenceTone,
  scorePercent,
} from "../../utils/format";
import { Badge } from "./Badge";

const barTone: Record<Confidence, string> = {
  TINGGI: "bg-primary-container",
  SEDANG: "bg-secondary",
  RENDAH: "bg-warning",
};

export function ConfidenceMeter({
  score,
  confidence,
}: {
  score: number;
  confidence: Confidence;
}) {
  const percent = scorePercent(score);
  return (
    <div className="space-y-2 rounded-2xl border border-border bg-surface-low p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-xs font-semibold uppercase tracking-wide text-muted">
          Skor kecocokan
        </span>
        <div className="flex items-center gap-2">
          <Badge tone={confidenceTone(confidence)}>
            {confidenceLabel(confidence)}
          </Badge>
          <span className="font-mono text-lg font-bold text-primary">
            {percent}%
          </span>
        </div>
      </div>
      <div
        className="h-2.5 overflow-hidden rounded-full bg-[#dbe5dc]"
        role="progressbar"
        aria-valuenow={percent}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Skor kecocokan kandidat"
      >
        <div
          className={`h-full rounded-full transition-all ${barTone[confidence]}`}
          style={{ width: `${percent}%` }}
        />
      </div>
      <p className="text-[11px] leading-5 text-muted">
        Skor ini adalah keluaran model reasoning, bukan probabilitas statistik
        atau certainty factor.
      </p>
    </div>
  );
}

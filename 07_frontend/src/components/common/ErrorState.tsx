import { AlertTriangle, RefreshCw } from "lucide-react";

import { Button } from "./Button";

export function ErrorState({
  title = "Terjadi kesalahan",
  message,
  onRetry,
}: {
  title?: string;
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div
      className="card flex flex-col items-start gap-3 border-warning/20 bg-[#fffaf5] p-6"
      role="alert"
    >
      <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#ffedd5] text-warning">
        <AlertTriangle className="h-5 w-5" aria-hidden="true" />
      </span>
      <div>
        <h3 className="font-heading text-base font-bold text-foreground">
          {title}
        </h3>
        <p className="mt-1 text-sm leading-6 text-muted">{message}</p>
      </div>
      {onRetry && (
        <Button variant="secondary" onClick={onRetry}>
          <RefreshCw className="h-4 w-4" aria-hidden="true" />
          Coba lagi
        </Button>
      )}
    </div>
  );
}

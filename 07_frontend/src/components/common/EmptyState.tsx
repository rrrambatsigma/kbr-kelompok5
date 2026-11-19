import { SearchX } from "lucide-react";
import type { ReactNode } from "react";

export function EmptyState({
  title,
  description,
  action,
  icon,
}: {
  title: string;
  description: string;
  action?: ReactNode;
  icon?: ReactNode;
}) {
  return (
    <div className="card flex flex-col items-center justify-center gap-3 px-6 py-14 text-center">
      <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-surface-low text-secondary">
        {icon ?? <SearchX className="h-6 w-6" aria-hidden="true" />}
      </span>
      <h3 className="font-heading text-lg font-bold text-foreground">
        {title}
      </h3>
      <p className="max-w-md text-sm leading-6 text-muted">{description}</p>
      {action && <div className="pt-2">{action}</div>}
    </div>
  );
}

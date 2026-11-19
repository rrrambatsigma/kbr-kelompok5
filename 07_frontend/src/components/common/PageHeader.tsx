import type { ReactNode } from "react";

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <header className="space-y-4">
      {eyebrow && <span className="eyebrow">{eyebrow}</span>}
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="max-w-3xl space-y-2">
          <h1 className="text-balance font-heading text-3xl font-extrabold tracking-tight text-primary sm:text-4xl">
            {title}
          </h1>
          {description && (
            <p className="max-w-2xl text-sm leading-7 text-muted sm:text-base">
              {description}
            </p>
          )}
        </div>
        {actions && <div className="flex flex-wrap gap-3">{actions}</div>}
      </div>
    </header>
  );
}

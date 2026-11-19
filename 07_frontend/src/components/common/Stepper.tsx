import { Check } from "lucide-react";

export interface StepItem {
  label: string;
  shortLabel?: string;
}

export function Stepper({
  steps,
  current,
}: {
  steps: StepItem[];
  current: number;
}) {
  return (
    <ol className="flex w-full items-start justify-between gap-2" aria-label="Tahapan">
      {steps.map((step, index) => {
        const number = index + 1;
        const completed = number < current;
        const active = number === current;
        return (
          <li key={step.label} className="flex flex-1 flex-col items-center gap-2">
            <div className="flex w-full items-center">
              <span
                className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                  completed
                    ? "bg-primary-container text-white"
                    : active
                      ? "bg-primary-container text-white ring-4 ring-primary-soft/40"
                      : "border-2 border-border bg-white text-muted"
                }`}
                aria-current={active ? "step" : undefined}
              >
                {completed ? (
                  <Check className="h-4 w-4" aria-hidden="true" />
                ) : (
                  number
                )}
              </span>
              {index < steps.length - 1 && (
                <span
                  className={`ml-2 h-0.5 flex-1 ${
                    completed ? "bg-primary-container" : "bg-border"
                  }`}
                  aria-hidden="true"
                />
              )}
            </div>
            <span
              className={`text-center text-[10px] font-semibold leading-tight sm:text-xs ${
                active ? "text-primary" : "text-muted"
              }`}
            >
              {step.shortLabel ?? step.label}
            </span>
          </li>
        );
      })}
    </ol>
  );
}

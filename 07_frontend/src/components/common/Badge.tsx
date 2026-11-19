import type { ReactNode } from "react";

type Tone = "success" | "warning" | "danger" | "neutral";

const toneClass: Record<Tone, string> = {
  success: "badge-success",
  warning: "badge-warning",
  danger: "badge-danger",
  neutral: "badge-neutral",
};

export function Badge({
  tone = "neutral",
  children,
  className = "",
}: {
  tone?: Tone;
  children: ReactNode;
  className?: string;
}) {
  return (
    <span className={`${toneClass[tone]} ${className}`}>{children}</span>
  );
}

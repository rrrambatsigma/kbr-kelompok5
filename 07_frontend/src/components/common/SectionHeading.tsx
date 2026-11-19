export function SectionHeading({
  eyebrow,
  title,
  description,
  align = "center",
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  align?: "center" | "left";
}) {
  return (
    <div
      className={
        align === "center"
          ? "mx-auto max-w-2xl space-y-3 text-center"
          : "max-w-2xl space-y-3"
      }
    >
      {eyebrow && (
        <p className="font-mono text-[11px] font-semibold uppercase tracking-[0.14em] text-secondary">
          {eyebrow}
        </p>
      )}
      <h2 className="text-balance font-heading text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
        {title}
      </h2>
      {description && (
        <p className="text-sm leading-7 text-muted sm:text-base">
          {description}
        </p>
      )}
    </div>
  );
}

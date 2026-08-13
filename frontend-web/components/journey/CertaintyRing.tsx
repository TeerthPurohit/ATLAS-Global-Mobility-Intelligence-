import { cn } from "@/lib/utils";
import type { Basis } from "@/lib/api";

interface CertaintyRingProps {
  basis: Basis;
  size?: number;
  className?: string;
  title?: string;
}

// The recurring "basis" motif (ADR-007): computed = solid brass ring (a
// confirmed reading), modeled_estimate = dashed verdigris ring (a proxy
// guess), unavailable = open corner brackets in muted oxide ("no reading",
// not an error alarm). Every PredictionField renders one of these.
export function CertaintyRing({ basis, size = 20, className, title }: CertaintyRingProps) {
  const r = size / 2 - 2;
  const c = size / 2;

  if (basis === "unavailable") {
    const gap = size * 0.28;
    return (
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className={className}>
        {title && <title>{title}</title>}
        {[0, 1, 2, 3].map((corner) => {
          const flipX = corner % 2 === 1 ? -1 : 1;
          const flipY = corner >= 2 ? -1 : 1;
          const ox = flipX === 1 ? 2 : size - 2;
          const oy = flipY === 1 ? 2 : size - 2;
          return (
            <path
              key={corner}
              d={`M ${ox} ${oy + flipY * gap} L ${ox} ${oy} L ${ox + flipX * gap} ${oy}`}
              fill="none"
              stroke="var(--oxide)"
              strokeWidth={1.5}
              strokeLinecap="round"
              opacity={0.7}
            />
          );
        })}
      </svg>
    );
  }

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className={cn(className)}>
      {title && <title>{title}</title>}
      <circle
        cx={c}
        cy={c}
        r={r}
        fill="none"
        stroke={basis === "computed" ? "var(--brass)" : "var(--verdigris)"}
        strokeWidth={2}
        strokeDasharray={basis === "modeled_estimate" ? "3 3" : undefined}
      />
    </svg>
  );
}

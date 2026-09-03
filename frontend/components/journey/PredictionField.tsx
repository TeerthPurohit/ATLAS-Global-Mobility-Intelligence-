import { cn } from "@/lib/utils";
import { formatCurrency, type PredictionOut } from "@/lib/api";
import { CertaintyRing } from "@/components/journey/CertaintyRing";
import { ProvenanceTooltip } from "@/components/ui/ProvenanceTooltip";

interface PredictionFieldProps {
  label: string;
  prediction: PredictionOut;
  className?: string;
  /** Gauge-face treatment for the highest-emphasis readouts (fare, confidence). */
  emphasis?: boolean;
  /** unit is an ISO 4217 currency code ("USD"/"INR"/"JPY") -- render via
   * Intl.NumberFormat (symbol, grouping, decimals per currency) instead of
   * a bare number + unit label. */
  isCurrency?: boolean;
}

function formatValue(value: PredictionOut["value"], unit: string | null, isCurrency: boolean): { text: string; suffix: string | null } {
  if (isCurrency && typeof value === "number" && unit) {
    return { text: formatCurrency(value, unit), suffix: null };
  }
  return { text: String(value ?? "--"), suffix: unit };
}

// The one place a PredictionOut becomes UI. Every screen renders predictions
// through this -- never inline -- so basis (ADR-007) is always visually
// distinguished via the CertaintyRing: computed (solid brass), modeled_estimate
// (dashed verdigris), unavailable (open oxide brackets, never blank/zero).
export function PredictionField({ label, prediction, className, emphasis, isCurrency }: PredictionFieldProps) {
  const { value, unit, basis, reason, data_vintage } = prediction;
  const { text: formattedValue, suffix } = formatValue(value, unit, Boolean(isCurrency));

  return (
    <div className={cn("flex items-start justify-between gap-3 py-2", className)} style={{ isolation: "isolate" }}>
      <div className="flex flex-col gap-1 group">
        <span className="flex items-center gap-1.5 text-xs uppercase tracking-wider text-ink-muted">
          <CertaintyRing basis={basis} size={14} title={reason ?? basis} />
          <span>{label}</span>
          <ProvenanceTooltip prediction={prediction} label={label} />
        </span>
        {basis === "unavailable" ? (
          <span className="font-mono text-sm text-ink-muted" title={reason ?? undefined}>
            no reading
          </span>
        ) : emphasis ? (
          <span className="inline-flex w-fit items-center rounded-lg bg-parchment px-3 py-1.5">
            <span className="font-mono text-lg font-semibold text-[#1b1a17]">
              {formattedValue}
              {suffix ? <span className="ml-1 text-xs font-normal text-[#4a4640]">{suffix}</span> : null}
            </span>
          </span>
        ) : (
          <span
            className={cn(
              "font-mono text-sm font-medium text-ink-primary",
              basis === "modeled_estimate" && "text-verdigris"
            )}
          >
            {formattedValue}
            {suffix ? <span className="ml-1 text-xs text-ink-muted">{suffix}</span> : null}
          </span>
        )}
        {reason && basis !== "unavailable" && (
          <span className="text-xs text-ink-muted">{reason}</span>
        )}
        {data_vintage && basis === "computed" && (
          <span className="text-[10px] text-ink-muted/70">data: {data_vintage}</span>
        )}
      </div>
    </div>
  );
}

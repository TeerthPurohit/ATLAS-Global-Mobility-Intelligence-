import Link from "next/link";
import { ArrowRight, Compass } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { CertaintyRing } from "@/components/journey/CertaintyRing";
import type { Basis } from "@/lib/api";

const basisRows: { basis: Basis; label: string; copy: string }[] = [
  {
    basis: "computed",
    label: "Computed",
    copy: "Read straight off the trip record or a deterministic query — a fact, not a guess.",
  },
  {
    basis: "modeled_estimate",
    label: "Modeled estimate",
    copy: "Produced by a trained model against historical patterns. Useful, and labeled as an estimate.",
  },
  {
    basis: "unavailable",
    label: "Not available",
    copy: "No reliable reading exists yet. Shown as an open bracket, never a fabricated number.",
  },
];

export default function LandingPage() {
  return (
    <div className="flex flex-col gap-16 py-8">
      <section className="flex flex-col items-start gap-6">
        <span className="flex items-center gap-2 text-xs uppercase tracking-widest text-ink-muted">
          <Compass className="h-4 w-4 text-brass" />
          Journey Intelligence Engine
        </span>
        <h1 className="max-w-2xl font-display text-4xl font-semibold leading-tight text-ink-primary sm:text-5xl">
          Know what your platform actually knows.
        </h1>
        <p className="max-w-xl text-base text-ink-secondary">
          Fare, ETA, demand, and risk for any two points in NYC — each reading marked as computed,
          modeled, or unavailable. No estimate pretends to be a fact.
        </p>
        <Link
          href="/journey"
          className="inline-flex items-center gap-2 rounded-xl bg-accent px-5 py-2.5 text-sm font-medium text-accent-fg transition-colors hover:opacity-90"
        >
          Plot a journey
          <ArrowRight className="h-4 w-4" />
        </Link>
      </section>

      <section className="flex flex-col gap-4">
        <h2 className="font-display text-xl font-semibold text-ink-primary">
          Every number carries its own confidence
        </h2>
        <p className="max-w-2xl text-sm text-ink-secondary">
          Instead of one flat fare and one flat ETA, each field on the journey readout is tagged with
          its basis. The Certainty Ring is the same symbol everywhere in the product:
        </p>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {basisRows.map((row) => (
            <Card key={row.basis} className="flex flex-col gap-3">
              <CertaintyRing basis={row.basis} size={24} />
              <div>
                <p className="text-sm font-semibold text-ink-primary">{row.label}</p>
                <p className="mt-1 text-xs text-ink-secondary">{row.copy}</p>
              </div>
            </Card>
          ))}
        </div>
      </section>
    </div>
  );
}

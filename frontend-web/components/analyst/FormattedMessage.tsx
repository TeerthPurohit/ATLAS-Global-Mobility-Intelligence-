"use client";

import { useMemo } from "react";
import { Sparkles, ArrowRight, Layers } from "lucide-react";
import { cn } from "@/lib/utils";

interface FormattedMessageProps {
  content: string;
  onPickPrompt?: (prompt: string) => void;
}

export function FormattedMessage({ content, onPickPrompt }: FormattedMessageProps) {
  const parsed = useMemo(() => {
    if (!content) return null;

    // Check if this is a structured numeric marts response
    // e.g. "Based on the marts:\n- Pickup Zone: Charleston/Tottenville, Fare: $95.01\n..."
    if (content.includes("Based on the marts:") || content.includes("- Pickup Zone:") || content.includes("- Total Trips:")) {
      const lines = content.split("\n").map((l) => l.trim()).filter(Boolean);
      const headerLine = lines.find((l) => l.startsWith("Based on the marts:")) || "Based on the marts:";
      const dataLines = lines.filter((l) => l.startsWith("- "));
      const footerLine = lines.find((l) => l.startsWith("(showing"));

      if (dataLines.length > 0) {
        const rows = dataLines.map((line) => {
          const clean = line.replace(/^-\s*/, "");
          const pairs = clean.split(/,\s*(?=[A-Za-z\s]+:)/).map((p) => {
            const idx = p.indexOf(":");
            if (idx === -1) return { key: "Value", val: p.trim() };
            return { key: p.slice(0, idx).trim(), val: p.slice(idx + 1).trim() };
          });
          return pairs;
        });

        return {
          type: "table" as const,
          header: headerLine,
          rows,
          footer: footerLine,
        };
      }
    }

    return { type: "text" as const };
  }, [content]);

  if (parsed?.type === "table") {
    return (
      <div className="flex flex-col gap-3">
        <p className="text-xs font-mono font-semibold text-brass flex items-center gap-1.5">
          <Layers className="h-3.5 w-3.5" />
          <span>{parsed.header}</span>
        </p>

        {/* Structured Results Card Grid */}
        <div className="flex flex-col gap-2 rounded-xl border border-surface-border bg-surface-0/60 p-2.5">
          {parsed.rows.map((rowPairs, rowIdx) => (
            <div
              key={rowIdx}
              className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 rounded-lg border border-surface-border/70 bg-surface-1 px-3.5 py-2.5 shadow-2xs transition-all hover:border-brass/40"
            >
              <div className="flex items-center gap-2.5">
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-md bg-brass/10 font-mono text-[11px] font-bold text-brass">
                  {rowIdx + 1}
                </span>
                <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                  {rowPairs.map((pair, pIdx) => {
                    const isFare = pair.key.toLowerCase().includes("fare") || pair.key.toLowerCase().includes("cost");
                    const isZone = pair.key.toLowerCase().includes("zone");
                    if (isFare) return null; // rendered on right

                    return (
                      <div key={pIdx} className="flex items-center gap-1.5 text-xs">
                        <span className="text-ink-muted font-medium">{pair.key}:</span>
                        <span className={cn("font-semibold", isZone ? "text-ink-primary" : "text-ink-secondary")}>
                          {pair.val}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Highlight metrics (Fare / Cost / Trips) */}
              <div className="flex items-center gap-2 font-mono text-xs">
                {rowPairs
                  .filter((p) => p.key.toLowerCase().includes("fare") || p.key.toLowerCase().includes("cost") || p.key.toLowerCase().includes("trips"))
                  .map((p, pIdx) => (
                    <div key={pIdx} className="rounded-md bg-brass/10 px-2.5 py-1 text-right font-bold text-brass">
                      <span className="text-[10px] uppercase text-ink-muted mr-1 font-sans">{p.key}:</span>
                      <span>{p.val}</span>
                    </div>
                  ))}
              </div>
            </div>
          ))}
        </div>

        {parsed.footer && (
          <p className="text-[11px] font-mono text-ink-muted">{parsed.footer}</p>
        )}
      </div>
    );
  }

  // Standard Markdown & Prompts Parser
  return <MarkdownBody text={content} onPickPrompt={onPickPrompt} />;
}

function MarkdownBody({ text, onPickPrompt }: { text: string; onPickPrompt?: (prompt: string) => void }) {
  const paragraphs = text.split(/\n\n+/);

  return (
    <div className="flex flex-col gap-3 leading-relaxed text-sm text-ink-primary font-body-md">
      {paragraphs.map((p, pIdx) => {
        // Check if paragraph is bullet list
        if (p.includes("\n- ") || p.startsWith("- ")) {
          const lines = p.split("\n").map((l) => l.trim()).filter(Boolean);
          const title = lines.find((l) => !l.startsWith("- "));
          const items = lines.filter((l) => l.startsWith("- "));

          return (
            <div key={pIdx} className="flex flex-col gap-2">
              {title && (
                <p className="font-semibold text-xs text-ink-primary font-mono uppercase tracking-wider">
                  {cleanMarkdown(title)}
                </p>
              )}
              <div className="flex flex-col gap-2">
                {items.map((item, iIdx) => {
                  const rawItem = item.replace(/^-\s*/, "");
                  const cleanItem = cleanMarkdown(rawItem);
                  const isPrompt = rawItem.startsWith("*") && rawItem.endsWith("*");

                  if (isPrompt && onPickPrompt) {
                    return (
                      <button
                        key={iIdx}
                        type="button"
                        onClick={() => onPickPrompt(cleanItem)}
                        className="group flex items-center justify-between rounded-xl border border-surface-border/80 bg-surface-0/70 px-3.5 py-2 text-left text-xs font-medium text-ink-secondary transition-all hover:border-brass/40 hover:bg-surface-1 hover:text-ink-primary hover:shadow-2xs"
                      >
                        <div className="flex items-center gap-2">
                          <Sparkles className="h-3.5 w-3.5 text-brass shrink-0 transition-transform group-hover:scale-110" />
                          <span>{cleanItem}</span>
                        </div>
                        <ArrowRight className="h-3.5 w-3.5 text-ink-muted opacity-60 transition-transform group-hover:translate-x-0.5 group-hover:opacity-100" />
                      </button>
                    );
                  }

                  return (
                    <div key={iIdx} className="flex items-start gap-2 text-xs">
                      <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-brass shrink-0" />
                      <span>{cleanItem}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        }

        return (
          <p key={pIdx} className="leading-relaxed">
            {formatInlineMarkdown(p)}
          </p>
        );
      })}
    </div>
  );
}

function cleanMarkdown(str: string): string {
  return str.replace(/\*\*(.*?)\*\*/g, "$1").replace(/\*(.*?)\*/g, "$1");
}

function formatInlineMarkdown(str: string) {
  // Regex to split by bold **...** and italic *...*
  const parts = str.split(/(\*\*.*?\*\*|\*.*?\*)/g);
  return parts.map((part, idx) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <strong key={idx} className="font-bold text-ink-primary">
          {part.slice(2, -2)}
        </strong>
      );
    }
    if (part.startsWith("*") && part.endsWith("*")) {
      return (
        <em key={idx} className="font-medium text-ink-primary not-italic">
          {part.slice(1, -1)}
        </em>
      );
    }
    return part;
  });
}

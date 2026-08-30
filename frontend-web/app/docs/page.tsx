"use client";

import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { getDocsSpec } from "@/lib/api";
import {
  Search,
  ChevronRight,
  ChevronDown,
  Copy,
  Check,
  Terminal,
  Code2,
  ExternalLink,
  BookOpen,
  Zap,
  Layers,
  Database,
  ShieldCheck,
  Play,
  ArrowRight,
  Sparkles,
  Server,
  FileCode,
  Compass,
  Cpu,
  GitBranch,
  Network,
  Activity,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";
import { motion } from "framer-motion";

export default function DocsPage() {
  const { data: spec } = useQuery({
    queryKey: ["docs", "spec"],
    queryFn: getDocsSpec,
    staleTime: 10 * 60_000,
  });

  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategoryId, setSelectedCategoryId] = useState<string>("getting-started");
  const [selectedLanguage, setSelectedLanguage] = useState<"curl" | "python" | "typescript">("curl");
  const [copiedCode, setCopiedCode] = useState<string | null>(null);

  // Interactive Live Tester state
  const [testEndpoint, setTestEndpoint] = useState<string>("/api/mobility/departure-time");
  const [testPayload, setTestPayload] = useState<string>(
    JSON.stringify(
      {
        pickup_lat: 40.758,
        pickup_lon: -73.9855,
        dropoff_lat: 40.6413,
        dropoff_lon: -73.7781,
        vehicle_type: "sedan",
      },
      null,
      2
    )
  );
  const [testResponse, setTestResponse] = useState<any | null>(null);
  const [testLoading, setTestLoading] = useState<boolean>(false);

  const categories = spec?.categories || [];

  const activeCategory = useMemo(() => {
    return categories.find((c: any) => c.id === selectedCategoryId) || categories[0];
  }, [categories, selectedCategoryId]);

  const activeCategoryIndex = useMemo(() => {
    return categories.findIndex((c: any) => c.id === selectedCategoryId);
  }, [categories, selectedCategoryId]);

  const prevCategory = activeCategoryIndex > 0 ? categories[activeCategoryIndex - 1] : null;
  const nextCategory = activeCategoryIndex < categories.length - 1 ? categories[activeCategoryIndex + 1] : null;

  const handleCopyCode = (code: string) => {
    navigator.clipboard.writeText(code);
    setCopiedCode(code);
    setTimeout(() => setCopiedCode(null), 2000);
  };

  const handleRunLiveTest = async () => {
    setTestLoading(true);
    setTestResponse(null);
    try {
      let parsed = {};
      try {
        parsed = JSON.parse(testPayload);
      } catch (e) {
        setTestResponse({ error: "Invalid JSON in request payload." });
        setTestLoading(false);
        return;
      }

      const res = await fetch(`http://localhost:8000${testEndpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(parsed),
      });
      const data = await res.json();
      setTestResponse(data);
    } catch (err: any) {
      setTestResponse({
        error: "Failed to connect to backend server (http://localhost:8000).",
        message: err.message,
      });
    } finally {
      setTestLoading(false);
    }
  };

  // Filtered categories based on search
  const filteredCategories = useMemo(() => {
    if (!categories) return [];
    if (!searchQuery.trim()) return categories;

    const q = searchQuery.toLowerCase();
    return categories.filter((cat: any) => {
      const matchCat = cat.title.toLowerCase().includes(q) || cat.description?.toLowerCase().includes(q);
      const matchSections = cat.sections?.some(
        (s: any) => s.title.toLowerCase().includes(q) || s.content?.toLowerCase().includes(q)
      );
      const matchEndpoints = cat.endpoints?.some(
        (e: any) =>
          e.path.toLowerCase().includes(q) ||
          e.summary?.toLowerCase().includes(q) ||
          e.description?.toLowerCase().includes(q)
      );
      return matchCat || matchSections || matchEndpoints;
    });
  }, [categories, searchQuery]);

  return (
    <div className="flex h-[calc(100dvh-5.5rem)] w-full gap-6 overflow-hidden">
      {/* ── LEFT NAVIGATION SIDEBAR (Hermes-Style) ── */}
      <aside className="hidden h-full w-72 shrink-0 flex-col rounded-2xl border border-surface-border bg-white dark:bg-surface-1 p-4 shadow-sm md:flex">
        {/* Search Bar with Shortcut hint */}
        <div className="relative mb-4">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-ink-muted" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search documentation..."
            className="w-full rounded-xl border border-surface-border bg-surface-0/70 py-2 pl-9 pr-10 text-xs text-ink-primary placeholder-ink-muted focus:outline-none focus:ring-2 focus:ring-brass/40"
          />
          <kbd className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded border border-surface-border bg-surface-1 px-1.5 py-0.5 font-mono text-[9px] text-ink-muted shadow-2xs">
            ⌘K
          </kbd>
        </div>

        {/* Categories Tree */}
        <div className="flex-1 overflow-y-auto pr-1 space-y-1.5 no-scrollbar">
          <div className="px-2 py-1 text-[10px] font-mono font-bold uppercase tracking-wider text-ink-muted">
            Documentation Chapters
          </div>
          {filteredCategories.map((cat: any) => {
            const isSelected = selectedCategoryId === cat.id;
            return (
              <button
                key={cat.id}
                type="button"
                onClick={() => {
                  setSelectedCategoryId(cat.id);
                  // Scroll main container to top
                  const mainEl = document.getElementById("docs-main-content");
                  if (mainEl) mainEl.scrollTop = 0;
                }}
                className={cn(
                  "flex w-full items-center justify-between rounded-xl px-3 py-2.5 text-left text-xs transition-all",
                  isSelected
                    ? "bg-amber-400 text-ink-primary font-bold shadow-xs"
                    : "text-ink-secondary hover:bg-surface-0 hover:text-ink-primary"
                )}
              >
                <div className="flex items-center gap-2.5 truncate">
                  {cat.id.includes("overview") && <Compass className="h-4 w-4 shrink-0" />}
                  {cat.id.includes("adrs") && <GitBranch className="h-4 w-4 shrink-0" />}
                  {cat.id.includes("algorithms") && <Cpu className="h-4 w-4 shrink-0" />}
                  {cat.id.includes("models") && <Layers className="h-4 w-4 shrink-0" />}
                  {cat.id.includes("schemas") && <Database className="h-4 w-4 shrink-0" />}
                  {cat.id.includes("mobility") && <Zap className="h-4 w-4 shrink-0" />}
                  {cat.id.includes("context") && <Activity className="h-4 w-4 shrink-0" />}
                  {cat.id.includes("marts") && <Server className="h-4 w-4 shrink-0" />}
                  {cat.id.includes("chat") && <Sparkles className="h-4 w-4 shrink-0" />}
                  {cat.id.includes("analytics") && <FileCode className="h-4 w-4 shrink-0" />}
                  <span className="truncate">{cat.title}</span>
                </div>
                <ChevronRight
                  className={cn("h-3.5 w-3.5 shrink-0 opacity-60", isSelected && "text-ink-primary opacity-100 font-bold")}
                />
              </button>
            );
          })}
        </div>

        {/* Footer Meta */}
        <div className="mt-auto border-t border-surface-border/80 pt-3 text-[11px] font-mono text-ink-muted flex items-center justify-between">
          <span>ATLAS Engine v2.4</span>
          <span className="text-emerald-600 font-semibold flex items-center gap-1">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
            1.4B+ Records Mart
          </span>
        </div>
      </aside>

      {/* ── MAIN DOCUMENTATION READING CANVAS ── */}
      <main
        id="docs-main-content"
        className="flex flex-1 flex-col overflow-y-auto rounded-2xl border border-surface-border bg-white dark:bg-surface-1 shadow-sm p-6 sm:p-10 no-scrollbar scroll-smooth"
      >
        {/* Breadcrumb Header */}
        <div className="mb-6 flex items-center gap-2 text-xs font-mono text-ink-muted">
          <span>Docs</span>
          <ChevronRight className="h-3 w-3" />
          <span>Chapter {activeCategoryIndex + 1}</span>
          <ChevronRight className="h-3 w-3" />
          <span className="text-brass font-bold">{activeCategory?.title}</span>
        </div>

        {/* ── HERO BANNER (Hermes-Style Quick Action Bar) ── */}
        <div className="mb-10 rounded-2xl border border-surface-border/80 bg-surface-0/60 p-6 sm:p-8">
          <div className="flex flex-wrap items-center gap-2 mb-3">
            <Badge className="bg-brass text-white font-mono text-[10px]">v2.4 Production</Badge>
            <Badge className="bg-teal-500/10 text-teal-700 font-mono text-[10px]">OpenAPI 3.1</Badge>
            <Badge className="bg-indigo-500/10 text-indigo-700 font-mono text-[10px]">1.4B+ NYC Records</Badge>
            <Badge className="bg-emerald-500/10 text-emerald-700 font-mono text-[10px]">Deterministic SQL</Badge>
          </div>

          <h1 className="font-display-lg text-3xl font-extrabold text-ink-primary sm:text-4xl">
            {activeCategory?.title || "ATLAS Mobility Intelligence Platform"}
          </h1>
          <p className="mt-3 text-sm text-ink-secondary leading-relaxed max-w-3xl">
            {activeCategory?.description ||
              "High-throughput urban spatial intelligence, real-time arterial congestion inference, and deterministic SQL grounding across 1.4B+ NYC TLC records."}
          </p>

          {/* Action CTAs (Gold Primary like Hermes Agent Docs) */}
          <div className="mt-6 flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={() => {
                const el = document.getElementById("interactive-tester");
                if (el) el.scrollIntoView({ behavior: "smooth" });
              }}
              className="flex items-center gap-2 rounded-xl bg-amber-400 hover:bg-amber-300 px-5 py-2.5 text-xs font-bold text-ink-primary shadow-xs transition-all"
            >
              <Play className="h-3.5 w-3.5 fill-current" />
              <span>Interactive API Playground</span>
            </button>

            <a
              href="/scalar"
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-2 rounded-xl border border-surface-border bg-surface-1 px-4 py-2.5 text-xs font-semibold text-ink-primary hover:border-brass/40 shadow-2xs transition-all"
            >
              <FileCode className="h-3.5 w-3.5 text-brass" />
              <span>Interactive Swagger UI</span>
              <ExternalLink className="h-3 w-3 text-ink-muted" />
            </a>

            <a
              href="http://localhost:8000/openapi.json"
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-2 rounded-xl border border-surface-border bg-surface-1 px-4 py-2.5 text-xs font-semibold text-ink-primary hover:border-brass/40 shadow-2xs transition-all"
            >
              <Code2 className="h-3.5 w-3.5 text-teal-600" />
              <span>Raw OpenAPI JSON</span>
              <ExternalLink className="h-3 w-3 text-ink-muted" />
            </a>
          </div>
        </div>

        {/* ── CHAPTER CONTENT (Continuous Reading Experience) ── */}
        <div className="space-y-12 max-w-4xl">
          {/* Render All Sections in Active Chapter */}
          {activeCategory?.sections?.map((sec: any) => (
            <section key={sec.id} id={sec.id} className="space-y-4 border-b border-surface-border/60 pb-10">
              <div className="flex items-center gap-2 text-brass">
                <span className="h-2 w-2 rounded-full bg-brass" />
                <h2 className="font-display-md text-2xl font-bold text-ink-primary">{sec.title}</h2>
              </div>
              <DocContentRenderer content={sec.content} />

              {/* Code Samples for Section if present */}
              {sec.code_samples && (
                <div className="mt-6 space-y-3">
                  <div className="flex items-center justify-between border-b border-surface-border pb-2">
                    <span className="font-mono text-xs font-bold text-ink-primary">Example Execution</span>
                    <LanguageSwitcher selected={selectedLanguage} onChange={setSelectedLanguage} />
                  </div>
                  <CodeSnippetBlock
                    code={sec.code_samples[selectedLanguage] || sec.code_samples.curl}
                    language={selectedLanguage}
                    copied={copiedCode === (sec.code_samples[selectedLanguage] || sec.code_samples.curl)}
                    onCopy={handleCopyCode}
                  />
                </div>
              )}
            </section>
          ))}

          {/* Render All Endpoints in Active Chapter */}
          {activeCategory?.endpoints?.map((ep: any) => (
            <section key={ep.id} id={ep.id} className="space-y-6 border-b border-surface-border/60 pb-12">
              <div>
                <div className="flex items-center gap-3 mb-2">
                  <span
                    className={cn(
                      "rounded-lg px-2.5 py-1 font-mono text-xs font-bold uppercase",
                      ep.method === "GET"
                        ? "bg-teal-500/10 text-teal-700 dark:text-teal-400"
                        : ep.method === "POST"
                        ? "bg-brass/10 text-brass"
                        : "bg-amber-500/10 text-amber-700"
                    )}
                  >
                    {ep.method}
                  </span>
                  <span className="font-mono text-sm font-bold text-ink-primary">{ep.path}</span>
                </div>
                <h2 className="text-2xl font-extrabold text-ink-primary">{ep.summary}</h2>
                <p className="mt-2 text-sm text-ink-secondary leading-relaxed">{ep.description}</p>
              </div>

              {/* Code Snippet Tabs */}
              <div className="space-y-3">
                <div className="flex items-center justify-between border-b border-surface-border pb-2">
                  <span className="font-mono text-xs font-bold text-ink-primary">Request Code Sample</span>
                  <LanguageSwitcher selected={selectedLanguage} onChange={setSelectedLanguage} />
                </div>
                <CodeSnippetBlock
                  code={
                    ep.code_samples?.[selectedLanguage] ||
                    `curl -X ${ep.method} "http://localhost:8000${ep.path}"`
                  }
                  language={selectedLanguage}
                  copied={
                    copiedCode ===
                    (ep.code_samples?.[selectedLanguage] ||
                      `curl -X ${ep.method} "http://localhost:8000${ep.path}"`)
                  }
                  onCopy={handleCopyCode}
                />
              </div>

              {/* Request Parameters Table */}
              {ep.parameters && ep.parameters.length > 0 && (
                <div className="space-y-3">
                  <h3 className="font-section-md text-sm font-bold text-ink-primary">Request Parameters</h3>
                  <div className="overflow-hidden rounded-xl border border-surface-border bg-surface-0 shadow-2xs">
                    <table className="w-full text-left text-xs">
                      <thead>
                        <tr className="border-b border-surface-border bg-surface-2/70 font-mono uppercase tracking-wider text-ink-muted">
                          <th className="px-4 py-3 font-bold">Parameter</th>
                          <th className="px-4 py-3 font-bold">Type</th>
                          <th className="px-4 py-3 font-bold">Required</th>
                          <th className="px-4 py-3 font-bold">Description</th>
                          <th className="px-4 py-3 font-bold">Example</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-surface-border/50">
                        {ep.parameters.map((param: any, pIdx: number) => (
                          <tr key={pIdx} className="hover:bg-surface-1/60 transition-colors">
                            <td className="px-4 py-3 font-mono font-bold text-brass">{param.name}</td>
                            <td className="px-4 py-3 font-mono text-ink-muted">
                              <span className="rounded bg-surface-1 border border-surface-border px-1.5 py-0.5 text-[10px]">
                                {param.type}
                              </span>
                            </td>
                            <td className="px-4 py-3">
                              {param.required ? (
                                <span className="rounded bg-rose-500/10 text-rose-600 font-mono text-[10px] font-semibold px-1.5 py-0.5">
                                  REQUIRED
                                </span>
                              ) : (
                                <span className="rounded bg-surface-1 text-ink-muted font-mono text-[10px] px-1.5 py-0.5">
                                  optional
                                </span>
                              )}
                            </td>
                            <td className="px-4 py-3 text-ink-secondary leading-relaxed">{param.description}</td>
                            <td className="px-4 py-3 font-mono text-ink-primary">{String(param.example)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Response Example Preview */}
              {ep.response_example && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="font-section-md text-sm font-bold text-ink-primary">Response Schema (200 OK)</h3>
                    <span className="rounded bg-emerald-500/10 text-emerald-700 font-mono text-[10px] font-semibold px-2 py-0.5">
                      application/json
                    </span>
                  </div>
                  <div className="relative rounded-2xl border border-surface-border bg-slate-950 p-4 text-xs font-mono text-emerald-400 overflow-x-auto shadow-sm">
                    <pre className="whitespace-pre">{JSON.stringify(ep.response_example, null, 2)}</pre>
                    <button
                      type="button"
                      onClick={() => handleCopyCode(JSON.stringify(ep.response_example, null, 2))}
                      className="absolute right-3 top-3 rounded-lg border border-slate-800 bg-slate-900 px-2 py-1 text-[10px] text-slate-400 hover:text-white transition-colors flex items-center gap-1"
                    >
                      {copiedCode === JSON.stringify(ep.response_example, null, 2) ? (
                        <Check className="h-3 w-3 text-emerald-400" />
                      ) : (
                        <Copy className="h-3 w-3" />
                      )}
                      <span>{copiedCode === JSON.stringify(ep.response_example, null, 2) ? "Copied" : "Copy JSON"}</span>
                    </button>
                  </div>
                </div>
              )}
            </section>
          ))}

          {/* ── INTERACTIVE LIVE TESTER CONSOLE ── */}
          <section id="interactive-tester" className="space-y-4 rounded-2xl border border-brass/30 bg-brass/5 p-6 sm:p-8">
            <div className="flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2 text-brass">
                  <Play className="h-4 w-4 fill-current" />
                  <h3 className="font-display-md text-lg font-bold text-ink-primary">Live API Test Playground</h3>
                </div>
                <p className="text-xs text-ink-secondary mt-1">
                  Execute live requests directly against your local ATLAS instance (`http://localhost:8000`).
                </p>
              </div>
              <Button
                onClick={handleRunLiveTest}
                disabled={testLoading}
                className="bg-amber-400 hover:bg-amber-300 text-ink-primary font-bold shadow-xs text-xs px-4 py-2"
              >
                {testLoading ? "Sending Request..." : "Run Test Request"}
              </Button>
            </div>

            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <div className="space-y-2">
                <label className="text-[11px] font-mono font-bold uppercase text-ink-muted">Request Payload (JSON)</label>
                <textarea
                  value={testPayload}
                  onChange={(e) => setTestPayload(e.target.value)}
                  rows={8}
                  className="w-full rounded-xl border border-surface-border bg-slate-950 p-3 font-mono text-xs text-slate-200 focus:outline-none focus:ring-2 focus:ring-brass"
                />
              </div>

              <div className="space-y-2">
                <label className="text-[11px] font-mono font-bold uppercase text-ink-muted">Live Server Response</label>
                <div className="h-[178px] rounded-xl border border-surface-border bg-slate-950 p-3 font-mono text-xs text-emerald-400 overflow-y-auto">
                  {testLoading ? (
                    <span className="text-slate-400 animate-pulse">Querying http://localhost:8000...</span>
                  ) : testResponse ? (
                    <pre className="whitespace-pre">{JSON.stringify(testResponse, null, 2)}</pre>
                  ) : (
                    <span className="text-slate-500">Click &quot;Run Test Request&quot; to execute live endpoint.</span>
                  )}
                </div>
              </div>
            </div>
          </section>

          {/* ── PREV / NEXT CHAPTER NAVIGATION FOOTER ── */}
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-t border-surface-border pt-8 mt-12">
            {prevCategory ? (
              <button
                type="button"
                onClick={() => {
                  setSelectedCategoryId(prevCategory.id);
                  const mainEl = document.getElementById("docs-main-content");
                  if (mainEl) mainEl.scrollTop = 0;
                }}
                className="group flex flex-col items-start rounded-xl border border-surface-border p-4 hover:border-brass/40 transition-all text-left w-full sm:w-1/2"
              >
                <span className="text-[10px] font-mono text-ink-muted uppercase">← Previous Chapter</span>
                <span className="font-bold text-sm text-ink-primary group-hover:text-brass transition-colors">
                  {prevCategory.title}
                </span>
              </button>
            ) : <div />}

            {nextCategory ? (
              <button
                type="button"
                onClick={() => {
                  setSelectedCategoryId(nextCategory.id);
                  const mainEl = document.getElementById("docs-main-content");
                  if (mainEl) mainEl.scrollTop = 0;
                }}
                className="group flex flex-col items-end rounded-xl border border-surface-border p-4 hover:border-brass/40 transition-all text-right w-full sm:w-1/2 ml-auto"
              >
                <span className="text-[10px] font-mono text-ink-muted uppercase">Next Chapter →</span>
                <span className="font-bold text-sm text-ink-primary group-hover:text-brass transition-colors">
                  {nextCategory.title}
                </span>
              </button>
            ) : <div />}
          </div>
        </div>
      </main>
    </div>
  );
}

function LanguageSwitcher({
  selected,
  onChange,
}: {
  selected: "curl" | "python" | "typescript";
  onChange: (lang: "curl" | "python" | "typescript") => void;
}) {
  return (
    <div className="flex items-center gap-1 rounded-xl border border-surface-border bg-surface-0/80 p-1">
      {(["curl", "python", "typescript"] as const).map((lang) => (
        <button
          key={lang}
          type="button"
          onClick={() => onChange(lang)}
          className={cn(
            "rounded-lg px-2.5 py-1 text-[11px] font-mono font-semibold uppercase transition-all",
            selected === lang
              ? "bg-amber-400 text-ink-primary font-bold shadow-2xs"
              : "text-ink-muted hover:text-ink-primary"
          )}
        >
          {lang}
        </button>
      ))}
    </div>
  );
}

function CodeSnippetBlock({
  code,
  language,
  copied,
  onCopy,
}: {
  code: string;
  language: string;
  copied: boolean;
  onCopy: (code: string) => void;
}) {
  return (
    <div className="relative rounded-2xl border border-surface-border bg-slate-950 p-4 text-xs font-mono text-slate-200 overflow-x-auto shadow-sm">
      <div className="flex items-center justify-between border-b border-slate-800/80 pb-2 mb-3 text-[10px] text-slate-400">
        <span className="uppercase">{language} snippet</span>
        <button
          type="button"
          onClick={() => onCopy(code)}
          className="flex items-center gap-1 rounded px-2 py-0.5 text-slate-400 hover:text-white transition-colors bg-slate-900 border border-slate-800"
        >
          {copied ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
          <span>{copied ? "Copied" : "Copy"}</span>
        </button>
      </div>
      <pre className="whitespace-pre leading-relaxed">{code}</pre>
    </div>
  );
}

function DocContentRenderer({ content }: { content: string }) {
  const parts = content.split(/(```[\s\S]*?```)/g);

  return (
    <div className="space-y-4 text-sm text-ink-secondary leading-relaxed">
      {parts.map((part, idx) => {
        if (part.startsWith("```")) {
          const lines = part.slice(3, -3).trim().split("\n");
          const lang = lines[0].trim();
          const code = lines.slice(1).join("\n");
          return (
            <div key={idx} className="my-4 rounded-xl border border-surface-border bg-slate-950 p-4 font-mono text-xs text-slate-200 overflow-x-auto">
              {lang && <div className="mb-2 text-[10px] uppercase text-slate-400 font-bold">{lang}</div>}
              <pre className="whitespace-pre leading-relaxed">{code || lines.join("\n")}</pre>
            </div>
          );
        }

        const paragraphs = part.split("\n\n");
        return (
          <div key={idx} className="space-y-4">
            {paragraphs.map((p, pIdx) => {
              const trimmed = p.trim();
              if (!trimmed) return null;

              if (trimmed.includes("|") && trimmed.split("\n").length >= 2) {
                const rows = trimmed.split("\n").filter((r) => r.includes("|"));
                const headerRow = rows[0].split("|").filter((c) => c.trim() !== "");
                const dataRows = rows.slice(2).map((r) => r.split("|").filter((c) => c.trim() !== ""));

                return (
                  <div key={pIdx} className="my-4 overflow-hidden rounded-xl border border-surface-border bg-surface-0 shadow-2xs">
                    <table className="w-full text-left text-xs">
                      <thead>
                        <tr className="border-b border-surface-border bg-surface-2/70 font-mono uppercase tracking-wider text-ink-muted">
                          {headerRow.map((h, hIdx) => (
                            <th key={hIdx} className="px-4 py-3 font-bold text-ink-primary">
                              {h.trim()}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-surface-border/50">
                        {dataRows.map((row, rIdx) => (
                          <tr key={rIdx} className="hover:bg-surface-1/60 transition-colors">
                            {row.map((cell, cIdx) => (
                              <td key={cIdx} className="px-4 py-3 font-mono text-ink-secondary">
                                {cell.trim().replace(/\*\*(.*?)\*\*/g, "$1")}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                );
              }

              if (trimmed.startsWith("### ")) {
                return (
                  <h3 key={pIdx} className="font-section-md text-lg font-bold text-ink-primary pt-2">
                    {trimmed.replace("### ", "")}
                  </h3>
                );
              }

              if (trimmed.startsWith("#### ")) {
                return (
                  <h4 key={pIdx} className="font-section-md text-base font-bold text-ink-primary pt-1">
                    {trimmed.replace("#### ", "")}
                  </h4>
                );
              }

              if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
                const items = trimmed.split("\n");
                return (
                  <ul key={pIdx} className="list-disc pl-5 space-y-1.5 text-xs text-ink-secondary">
                    {items.map((it, itIdx) => (
                      <li key={itIdx}>
                        {it.replace(/^[-*]\s+/, "")}
                      </li>
                    ))}
                  </ul>
                );
              }

              return (
                <p key={pIdx} className="text-xs text-ink-secondary leading-relaxed">
                  {trimmed}
                </p>
              );
            })}
          </div>
        );
      })}
    </div>
  );
}

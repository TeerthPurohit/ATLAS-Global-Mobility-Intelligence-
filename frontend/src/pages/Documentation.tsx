import React, { useState } from "react";
import {
  FileText,
  BookOpen,
  Check,
  Copy,
  Info,
  AlertTriangle,
  Lightbulb,
  ShieldAlert,
  Clock,
  Calendar,
  Tag,
  ChevronRight,
  ArrowLeft,
  ArrowRight,
} from "lucide-react";

interface DocItem {
  id: string;
  category: "Core Rules" | "Architecture ADRs" | "Specifications" | "Developer Guides";
  title: string;
  subtitle: string;
  version: string;
  lastUpdated: string;
  readingTime: string;
  toc: string[];
  content: {
    section: string;
    body: string;
    callout?: { type: "note" | "tip" | "warning"; title: string; text: string };
    code?: { lang: string; snippet: string };
    table?: { headers: string[]; rows: string[][] };
  }[];
}

const DOCUMENTATION_DATABASE: DocItem[] = [
  {
    id: "constitution",
    category: "Core Rules",
    title: "CLAUDE.md — Project Constitution",
    subtitle: "Mission, architecture guidelines, and foundational rules for the NYC Ride Intelligence Platform",
    version: "v2.0",
    lastUpdated: "2026-08-06",
    readingTime: "4 min read",
    toc: ["Mission Statement", "System Architecture & Layer Stack", "The One-Paragraph Philosophy", "AI Tooling Scaffold"],
    content: [
      {
        section: "Mission Statement",
        body: "Build an applied data engineering and ML platform on NYC TLC trip data demonstrating analytical SQL (dbt/DuckDB), classical algorithms (KD-tree, PageRank, Dijkstra, EWMA), a model ladder (linear → EWMA → XGBoost → LSTM) evaluated honestly on a chronological split, and a hybrid RAG layer that routes numeric questions to SQL and explanatory questions to vector retrieval.",
        callout: {
          type: "note",
          title: "Solo Builder Context",
          text: "This is a solo portfolio project (~12hrs/week). Every process document exists to make the engineering legible in an interview and to keep a single person from losing the thread across a 9-week build.",
        },
      },
      {
        section: "System Architecture & Layer Stack",
        body: "The platform is structured into 6 sequential layers:",
        table: {
          headers: ["Layer", "Component", "Primary Technologies", "Status"],
          rows: [
            ["0", "Data Foundation", "DuckDB, PyArrow, Parquet Ingestion", "Completed"],
            ["1", "dbt Transformation", "dbt-duckdb, Analytical Marts", "Completed"],
            ["2", "Classical Algorithms", "KD-Tree, PageRank, Dijkstra, EWMA", "Completed"],
            ["3", "Model Ladder", "Linear, EWMA, XGBoost, LSTM", "Completed"],
            ["4", "Hybrid RAG", "Qdrant, Sentence-Transformers, OpenAI", "Completed"],
            ["5", "Serving & UI", "FastAPI, React, TypeScript, Leaflet", "Completed"],
          ],
        },
      },
      {
        section: "The One-Paragraph Philosophy",
        body: "This is primarily a data engineering and ML platform. LLMs are tooling used in two places only: the RAG chat layer (Layer 4) and drafting phrasing for generated insight text. Everywhere else — aggregation, filtering, ranking, routing, nearest-neighbor lookup, forecasting — prefer SQL, a named algorithm, or a trained model over an LLM call.",
      },
    ],
  },
  {
    id: "rules",
    category: "Core Rules",
    title: "rules.md — Non-Negotiable Engineering Rules",
    subtitle: "Strict constraints governing SQL precedence, evaluation metrics, and split boundaries",
    version: "v1.4",
    lastUpdated: "2026-08-05",
    readingTime: "5 min read",
    toc: ["Rule 1: SQL over LLM", "Rule 2: Zero Fabricated Metrics", "Rule 3: Chronological Splits", "Rule 8: Artifact Loading"],
    content: [
      {
        section: "Rule 1: SQL over LLM",
        body: "Numeric questions (e.g. 'What is the average fare from JFK?') MUST route to SQL queries executed against DuckDB analytical marts. Never allow an LLM to generate or calculate numbers.",
        callout: {
          type: "tip",
          title: "Grounding Enforcement",
          text: "If an explanatory LLM response introduces any number not present in the retrieved vector document context, validate_grounding() rejects the rewrite and falls back to raw doc text.",
        },
      },
      {
        section: "Rule 2: Zero Fabricated Metrics",
        body: "Report true measured metrics from holdout test sets. Never fake a metric, smooth a loss curve, or pad performance figures. If a model performs poorly (e.g. LSTM capped at 3 CPU epochs), report it honestly.",
      },
      {
        section: "Rule 3: Chronological Splits",
        body: "Demand and fare models must split on whole-timestamp boundaries. Concatenating 3 disjoint monthly blocks (Jan, Mar, Jun) and using a raw row cutoff would slice single hourly timestamps across train and test.",
        code: {
          lang: "python",
          snippet: `def split_demand_blocks(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    # Cut strictly on timestamp boundaries to prevent data leakage
    train_val = df[df["ts"] < "2024-06-01"]
    test = df[df["ts"] >= "2024-06-01"]
    return train_val, test`,
        },
      },
    ],
  },
  {
    id: "adr004",
    category: "Architecture ADRs",
    title: "ADR-004: Hybrid RAG & NL-to-SQL Architecture",
    subtitle: "Architectural Decision Record governing query classification and retrieval paths",
    version: "v1.0",
    lastUpdated: "2026-08-05",
    readingTime: "6 min read",
    toc: ["Context & Problem Statement", "Decision Drivers", "Selected Architecture", "Consequences"],
    content: [
      {
        section: "Context & Problem Statement",
        body: "Users ask two distinct types of questions: precise aggregate metrics ('average fare in zone 132') and causal explanations ('why is JFK busy'). Single-path RAG pipelines struggle to answer exact SQL aggregates accurately.",
      },
      {
        section: "Selected Architecture",
        body: "Dual-path routing architecture:",
        callout: {
          type: "note",
          title: "Dual Routing Specification",
          text: "Numeric questions route to sql_agent.py (DuckDB NL-to-SQL). Explanatory questions route to Qdrant vector retrieval over precomputed insight docs.",
        },
        table: {
          headers: ["Intent Route", "Agent Handler", "Primary Storage", "LLM Role"],
          rows: [
            ["Numeric Intent", "sql_agent.py", "DuckDB Marts", "NL-to-SQL Generation"],
            ["Explanatory Intent", "vector_search()", "Qdrant Vector DB", "Phrasing Synthesis Only"],
          ],
        },
      },
    ],
  },
  {
    id: "global-domain-api",
    category: "Specifications",
    title: "SPEC-013: Global Mobility Domain Model API",
    subtitle: "Country -> City -> Area hierarchy discovery and city-scoped prediction contracts",
    version: "v1.0",
    lastUpdated: "2026-08-08",
    readingTime: "5 min read",
    toc: ["Geography Discovery", "Global Mobility Model", "Error Envelope Standards"],
    content: [
      {
        section: "Geography Discovery",
        body: "Endpoints under /api/geography/* provide world, country, and place hierarchy lookups backed by GeoNames with Google Places fallback.",
      },
      {
        section: "Global Mobility Model",
        body: "Country, city, area, metric, and forecast discovery routes backed by dbt seeds and live FastAPI registries.",
        table: {
          headers: ["Route", "Method", "Response Schema", "Description"],
          rows: [
            ["/api/countries", "GET", "{ countries: Country[] }", "List all countries with supported status"],
            ["/api/countries/{code}/cities", "GET", "City[]", "List onboarded cities for a country"],
            ["/api/cities/{city_id}/capabilities", "GET", "Capabilities", "Real wired city capabilities"],
            ["/api/cities/{city_id}/areas", "GET", "Area[]", "List canonical geographic areas"],
            ["/api/cities/{city_id}/predict/demand", "POST", "PredictionEnvelope", "City-scoped demand prediction"],
            ["/api/cities/{city_id}/forecast", "GET", "ForecastEnvelope", "City-scoped aggregate hourly profile"],
            ["/api/cities/{city_id}/chat", "POST", "ChatResponse", "City-scoped hybrid RAG chat"],
          ],
        },
      },
    ],
  },

];

export const Documentation: React.FC = () => {
  const [selectedDocId, setSelectedDocId] = useState<string>("constitution");
  const [copiedCode, setCopiedCode] = useState<string | null>(null);

  const doc = DOCUMENTATION_DATABASE.find((d) => d.id === selectedDocId) || DOCUMENTATION_DATABASE[0];

  const handleCopyCode = (codeText: string) => {
    navigator.clipboard.writeText(codeText);
    setCopiedCode(codeText);
    setTimeout(() => setCopiedCode(null), 2000);
  };

  const currentIndex = DOCUMENTATION_DATABASE.findIndex((d) => d.id === doc.id);
  const prevDoc = DOCUMENTATION_DATABASE[currentIndex - 1];
  const nextDoc = DOCUMENTATION_DATABASE[currentIndex + 1];

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-lg font-bold text-slate-100 flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-brand-400" />
            Architecture & Specifications Library
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Stripe Docs / Notion grade documentation reader rendering project constitution, rules, and ADRs
          </p>
        </div>
        <div className="flex items-center space-x-2 text-xs text-slate-400 font-mono">
          <span className="px-2.5 py-1 rounded-full bg-slate-900 border border-slate-800 flex items-center gap-1.5">
            <Tag className="w-3 h-3 text-brand-400" />
            {doc.version}
          </span>
          <span className="px-2.5 py-1 rounded-full bg-slate-900 border border-slate-800 flex items-center gap-1.5">
            <Clock className="w-3 h-3 text-indigo-400" />
            {doc.readingTime}
          </span>
        </div>
      </div>

      {/* Main Reading Layout: 3 Columns */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Categorized Document Navigation (3 cols) */}
        <aside className="lg:col-span-3 bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-4">
          <h3 className="text-[10px] font-bold uppercase tracking-wider text-slate-500 px-2">
            Documentation Index
          </h3>
          <div className="space-y-3">
            {["Core Rules", "Architecture ADRs", "Specifications"].map((cat) => {
              const catDocs = DOCUMENTATION_DATABASE.filter((d) => d.category === cat);
              if (catDocs.length === 0) return null;
              return (
                <div key={cat} className="space-y-1">
                  <span className="text-[11px] font-semibold text-slate-400 px-2 block">{cat}</span>
                  {catDocs.map((d) => (
                    <button
                      key={d.id}
                      onClick={() => setSelectedDocId(d.id)}
                      className={`w-full text-left px-3 py-2 rounded-lg text-xs font-medium transition-all flex items-center justify-between ${
                        selectedDocId === d.id
                          ? "bg-brand-600/20 text-brand-400 border border-brand-500/30"
                          : "text-slate-300 hover:bg-slate-800/60"
                      }`}
                    >
                      <span className="truncate">{d.title.split(" — ")[0]}</span>
                      <ChevronRight className="w-3.5 h-3.5 text-slate-600 shrink-0" />
                    </button>
                  ))}
                </div>
              );
            })}
          </div>
        </aside>

        {/* Middle Column: Document Reader Content (6 cols) */}
        <main className="lg:col-span-6 bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-6">
          {/* Document Header */}
          <div className="border-b border-slate-800 pb-4 space-y-2">
            <span className="text-[10px] font-mono font-bold uppercase text-brand-400">{doc.category}</span>
            <h2 className="text-xl font-bold text-slate-100">{doc.title}</h2>
            <p className="text-xs text-slate-400 leading-relaxed">{doc.subtitle}</p>
          </div>

          {/* Render Sections */}
          {doc.content.map((sec, idx) => (
            <section key={idx} id={`sec-${idx}`} className="space-y-3 pt-2">
              <h3 className="text-sm font-bold text-slate-100 border-b border-slate-800/60 pb-1.5 flex items-center gap-2">
                <span className="text-brand-400 font-mono text-xs">#</span>
                {sec.section}
              </h3>

              <p className="text-xs text-slate-300 leading-relaxed">{sec.body}</p>

              {/* Render Callout Admonition */}
              {sec.callout && (
                <div
                  className={`p-4 rounded-xl border text-xs leading-relaxed space-y-1 ${
                    sec.callout.type === "note"
                      ? "bg-brand-500/10 border-brand-500/30 text-brand-200"
                      : sec.callout.type === "tip"
                      ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-200"
                      : "bg-amber-500/10 border-amber-500/30 text-amber-200"
                  }`}
                >
                  <div className="flex items-center space-x-2 font-bold">
                    {sec.callout.type === "note" && <Info className="w-4 h-4 text-brand-400" />}
                    {sec.callout.type === "tip" && <Lightbulb className="w-4 h-4 text-emerald-400" />}
                    {sec.callout.type === "warning" && <AlertTriangle className="w-4 h-4 text-amber-400" />}
                    <span>{sec.callout.title}</span>
                  </div>
                  <p className="text-[11px] opacity-90">{sec.callout.text}</p>
                </div>
              )}

              {/* Render Code Block */}
              {sec.code && (
                <div className="rounded-xl bg-slate-950 border border-slate-800 overflow-hidden font-mono text-xs">
                  <div className="flex items-center justify-between px-4 py-2 border-b border-slate-800 bg-slate-950/80 text-[10px] text-slate-400">
                    <span>{sec.code.lang}</span>
                    <button
                      onClick={() => handleCopyCode(sec.code!.snippet)}
                      className="flex items-center space-x-1 hover:text-slate-200 transition-colors"
                    >
                      {copiedCode === sec.code.snippet ? (
                        <Check className="w-3.5 h-3.5 text-emerald-400" />
                      ) : (
                        <Copy className="w-3.5 h-3.5" />
                      )}
                      <span>{copiedCode === sec.code.snippet ? "Copied!" : "Copy"}</span>
                    </button>
                  </div>
                  <pre className="p-4 text-emerald-400 overflow-x-auto whitespace-pre-wrap leading-relaxed">
                    {sec.code.snippet}
                  </pre>
                </div>
              )}

              {/* Render Table */}
              {sec.table && (
                <div className="overflow-x-auto rounded-xl border border-slate-800">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-950 text-slate-400 font-semibold uppercase text-[10px] border-b border-slate-800">
                      <tr>
                        {sec.table.headers.map((h, i) => (
                          <th key={i} className="p-3">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800 text-slate-200">
                      {sec.table.rows.map((row, i) => (
                        <tr key={i} className="hover:bg-slate-800/40">
                          {row.map((cell, j) => (
                            <td key={j} className="p-3 font-mono text-[11px]">{cell}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          ))}

          {/* Next / Previous Navigation Footer */}
          <div className="pt-6 border-t border-slate-800 flex items-center justify-between">
            {prevDoc ? (
              <button
                onClick={() => setSelectedDocId(prevDoc.id)}
                className="flex items-center space-x-2 text-xs text-slate-400 hover:text-brand-400 transition-colors"
              >
                <ArrowLeft className="w-4 h-4" />
                <span>{prevDoc.title.split(" — ")[0]}</span>
              </button>
            ) : <div />}

            {nextDoc && (
              <button
                onClick={() => setSelectedDocId(nextDoc.id)}
                className="flex items-center space-x-2 text-xs text-slate-400 hover:text-brand-400 transition-colors"
              >
                <span>{nextDoc.title.split(" — ")[0]}</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            )}
          </div>
        </main>

        {/* Right Column: Sticky Table of Contents (3 cols) */}
        <aside className="lg:col-span-3 bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3 sticky top-20">
          <h4 className="text-[10px] font-bold uppercase tracking-wider text-slate-500 px-1">
            On This Page
          </h4>
          <nav className="space-y-1">
            {doc.toc.map((head, idx) => (
              <a
                key={idx}
                href={`#sec-${idx}`}
                className="block text-xs text-slate-400 hover:text-brand-400 py-1 px-2 rounded hover:bg-slate-800/50 transition-colors truncate"
              >
                {head}
              </a>
            ))}
          </nav>
        </aside>
      </div>
    </div>
  );
};

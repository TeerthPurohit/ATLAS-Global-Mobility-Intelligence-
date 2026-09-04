"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Send,
  Bot,
  Sparkles,
  Database,
  Plus,
  Trash2,
  Square,
  MessageSquare,
  Compass,
  RotateCcw,
  Copy,
  Check,
  Zap,
  Activity,
  Layers,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { cn } from "@/lib/utils";
import {
  getChatHistory,
  streamChat,
  createChatSession,
  listChatSessions,
  deleteChatSession,
  type ChatMessage,
  type ChatRoute,
  type ChatSessionSummary,
} from "@/lib/api";
import { motion, AnimatePresence } from "framer-motion";
import { PulsingStatusDot } from "@/components/magic/PulsingStatusDot";
import { useAuth } from "@/context/AuthContext";
import { FormattedMessage } from "@/components/analyst/FormattedMessage";

interface Turn {
  role: "user" | "assistant";
  content: string;
  route?: ChatRoute | null;
  sql?: string | null;
  pending?: boolean;
  modelLabel?: string | null;
}

const SESSION_KEY = "analyst_session_id";

export default function AnalystPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string | undefined>(undefined);
  const [wsError, setWsError] = useState<string | null>(null);
  const [streaming, setStreaming] = useState(false);
  const [sessions, setSessions] = useState<ChatSessionSummary[]>([]);
  const closeRef = useRef<(() => void) | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!authLoading && !user) router.push("/login");
  }, [authLoading, user, router]);

  const refreshSessions = useCallback(() => {
    listChatSessions()
      .then(setSessions)
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (authLoading || !user) return;
    refreshSessions();
    // Always start with a fresh, empty conversation on initial entry (like ChatGPT)
    setSessionId(undefined);
    setTurns([]);
    setWsError(null);
    localStorage.removeItem(SESSION_KEY);
  }, [authLoading, user, refreshSessions]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns]);

  useEffect(() => () => closeRef.current?.(), []);

  function finalizePending() {
    setStreaming(false);
    setTurns((prev) => {
      const last = prev[prev.length - 1];
      if (!last?.pending) return prev;
      const next = [...prev];
      next[next.length - 1] = { ...last, pending: false };
      return next;
    });
  }

  function stopGenerating() {
    closeRef.current?.();
    closeRef.current = null;
    finalizePending();
  }

  function ask(question: string) {
    if (!question.trim()) return;
    setWsError(null);
    setInput("");
    setStreaming(true);
    setTurns((prev) => [
      ...prev,
      { role: "user", content: question },
      { role: "assistant", content: "", pending: true },
    ]);

    closeRef.current = streamChat(
      { question, session_id: sessionId },
      {
        onFrame: (frame) => {
          if ("error" in frame) {
            setStreaming(false);
            setWsError(frame.error);
            setTurns((prev) => {
              const next = [...prev];
              next[next.length - 1] = {
                role: "assistant",
                content: frame.error,
              };
              return next;
            });
            return;
          }
          if (frame.type === "model") {
            setTurns((prev) => {
              const next = [...prev];
              const last = next[next.length - 1];
              next[next.length - 1] = { ...last, modelLabel: frame.label };
              return next;
            });
          } else if (frame.type === "chunk") {
            setTurns((prev) => {
              const next = [...prev];
              const last = next[next.length - 1];
              next[next.length - 1] = {
                ...last,
                content: last.content + frame.text,
                pending: true,
              };
              return next;
            });
          } else if (frame.type === "done") {
            const { payload } = frame;
            setStreaming(false);
            if (payload.session_id && payload.session_id !== sessionId) {
              setSessionId(payload.session_id);
              localStorage.setItem(SESSION_KEY, payload.session_id);
            }
            setTurns((prev) => {
              const next = [...prev];
              next[next.length - 1] = {
                role: "assistant",
                content: payload.answer,
                route: payload.route,
                sql: payload.sql,
                pending: false,
              };
              return next;
            });
            refreshSessions();
          }
        },
        onError: () => {
          setStreaming(false);
          setWsError("Connection interrupted. Please ensure the backend service is running and retry.");
          setTurns((prev) => {
            if (prev.length === 0) return prev;
            const last = prev[prev.length - 1];
            if (last.role === "assistant" && !last.content) {
              const next = [...prev];
              next[next.length - 1] = {
                role: "assistant",
                content: "⚠️ Connection was interrupted while retrieving data. Please retry your question.",
                pending: false,
              };
              return next;
            }
            return prev;
          });
        },
        onClose: finalizePending,
      }
    );
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    ask(input);
  }

  async function newChat() {
    if (streaming) stopGenerating();
    const { session_id } = await createChatSession();
    setSessionId(session_id);
    setTurns([]);
    setWsError(null);
    localStorage.setItem(SESSION_KEY, session_id);
    refreshSessions();
  }

  async function selectSession(id: string) {
    if (id === sessionId) return;
    if (streaming) stopGenerating();
    setSessionId(id);
    localStorage.setItem(SESSION_KEY, id);
    setWsError(null);
    const history = await getChatHistory(id);
    setTurns(
      history.map((m: ChatMessage) => ({
        role: m.role === "user" ? "user" : "assistant",
        content: m.content,
        route: m.route,
        sql: m.sql,
      }))
    );
  }

  async function handleDeleteSession(id: string, e: React.MouseEvent) {
    e.stopPropagation();
    if (!window.confirm("Delete this conversation thread?")) return;
    await deleteChatSession(id);
    if (id === sessionId) {
      setSessionId(undefined);
      setTurns([]);
      localStorage.removeItem(SESSION_KEY);
    }
    refreshSessions();
  }

  if (authLoading || !user) {
    return (
      <div className="flex h-full items-center justify-center py-24">
        <p className="font-body-md text-ink-secondary">
          {authLoading ? "Authenticating session..." : "Redirecting to login..."}
        </p>
      </div>
    );
  }

  return (
    <div className="flex h-[calc(100dvh-6.5rem)] w-full gap-5 overflow-hidden">
      {/* Left Sidebar */}
      <SessionSidebar
        sessions={sessions}
        activeSessionId={sessionId}
        onNewChat={newChat}
        onSelect={selectSession}
        onDelete={handleDeleteSession}
      />

      {/* Main Conversation Container */}
      <div className="flex flex-1 flex-col overflow-hidden rounded-3xl border border-surface-border bg-surface-1/80 shadow-xs backdrop-blur-xl">
        {/* Header Bar */}
        <div className="flex items-center justify-between border-b border-surface-border/80 bg-surface-1/90 px-6 py-3.5 backdrop-blur-md">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-brass/15 text-brass">
              <Compass className="h-4 w-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-section-md text-sm font-bold text-ink-primary">
                  AI Spatial Mobility Analyst
                </span>
                <span className="rounded bg-brass/10 px-2 py-0.2 text-[10px] font-mono font-semibold uppercase text-brass">
                  Dual NL-to-SQL + RAG
                </span>
              </div>
              <span className="text-[11px] font-mono text-ink-muted">
                1.4B+ Records Mart Ground Truth
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {turns.length > 0 && (
              <Button
                variant="secondary"
                onClick={() => setTurns([])}
                className="gap-1.5 py-1 px-2.5 text-xs text-ink-secondary hover:text-ink-primary"
              >
                <RotateCcw className="h-3.5 w-3.5" />
                <span>Clear view</span>
              </Button>
            )}
            <div className="flex items-center gap-1.5 rounded-full border border-surface-border bg-surface-0/80 px-2.5 py-1 text-xs text-ink-secondary">
              <PulsingStatusDot status="live" size={6} />
              <span className="text-[11px] font-mono">TLC Stream Ready</span>
            </div>
          </div>
        </div>

        {/* Message Stream Viewport */}
        <div className="flex-1 overflow-y-auto px-4 py-6 sm:px-8">
          <div className="mx-auto flex max-w-3xl flex-col gap-6">
            {turns.length === 0 ? (
              <EmptyState onPick={ask} />
            ) : (
              <div className="flex flex-col gap-6">
                <AnimatePresence initial={false}>
                  {turns.map((turn, i) => (
                    <TurnBubble key={i} turn={turn} onPickPrompt={(prompt) => ask(prompt)} />
                  ))}
                </AnimatePresence>
                <div ref={bottomRef} />
              </div>
            )}
          </div>
        </div>

        {/* Error Banner */}
        {wsError && (
          <div className="mx-auto w-full max-w-3xl px-4">
            <div className="flex items-center justify-between rounded-xl border border-danger/30 bg-danger/10 px-4 py-2.5 text-xs text-danger">
              <p>{wsError}</p>
              <button
                type="button"
                onClick={() => setWsError(null)}
                className="ml-3 font-semibold underline"
              >
                Dismiss
              </button>
            </div>
          </div>
        )}

        {/* Sticky Elevated Input Bar */}
        <div className="border-t border-surface-border/80 bg-surface-1/95 p-4 backdrop-blur-md">
          <div className="mx-auto flex max-w-3xl flex-col gap-2.5">
            {/* Quick Suggestion Pills */}
            <div className="flex items-center gap-2 overflow-x-auto pb-1 text-xs no-scrollbar">
              <span className="shrink-0 text-[11px] font-mono text-ink-muted">Quick query:</span>
              <button
                type="button"
                onClick={() => ask("What is the average fare from JFK Airport?")}
                className="shrink-0 rounded-full border border-surface-border bg-surface-0/70 px-3 py-1 text-ink-secondary transition-colors hover:border-brass/50 hover:bg-surface-1 hover:text-ink-primary"
              >
                ✈️ JFK Avg Fare
              </button>
              <button
                type="button"
                onClick={() => ask("List top 5 pickup locations ranked by total trips.")}
                className="shrink-0 rounded-full border border-surface-border bg-surface-0/70 px-3 py-1 text-ink-secondary transition-colors hover:border-brass/50 hover:bg-surface-1 hover:text-ink-primary"
              >
                📊 Top 5 Pickup Zones
              </button>
              <button
                type="button"
                onClick={() => ask("Why is Zone 161 (Midtown) such a high-volume corridor?")}
                className="shrink-0 rounded-full border border-surface-border bg-surface-0/70 px-3 py-1 text-ink-secondary transition-colors hover:border-brass/50 hover:bg-surface-1 hover:text-ink-primary"
              >
                🏙️ Midtown Rush Hour Flow
              </button>
            </div>

            {/* Input Form */}
            <form onSubmit={handleSubmit} className="relative flex items-center gap-2">
              <div className="relative flex flex-1 items-center">
                <Input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Ask about fares, surge curves, zone demand, or TLC mart SQL..."
                  className="h-12 w-full rounded-2xl border-surface-border bg-surface-0/70 pl-4 pr-12 text-sm shadow-xs transition-all focus:border-brass/60 focus:bg-surface-1"
                  disabled={streaming}
                />
              </div>

              {streaming ? (
                <Button
                  type="button"
                  variant="secondary"
                  onClick={stopGenerating}
                  className="h-12 rounded-2xl px-5 font-medium shadow-xs"
                >
                  <Square className="h-4 w-4" />
                </Button>
              ) : (
                <Button
                  type="submit"
                  disabled={!input.trim()}
                  className="h-12 rounded-2xl px-5 font-semibold shadow-sm transition-transform active:scale-[0.98]"
                >
                  <Send className="h-4 w-4" />
                </Button>
              )}
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}

function SessionSidebar({
  sessions,
  activeSessionId,
  onNewChat,
  onSelect,
  onDelete,
}: {
  sessions: ChatSessionSummary[];
  activeSessionId: string | undefined;
  onNewChat: () => void;
  onSelect: (id: string) => void;
  onDelete: (id: string, e: React.MouseEvent) => void;
}) {
  return (
    <aside className="hidden h-full w-72 shrink-0 flex-col rounded-3xl border border-surface-border bg-surface-1/90 p-4 shadow-xs backdrop-blur-xl md:flex">
      {/* New Chat Button */}
      <Button
        variant="primary"
        onClick={onNewChat}
        className="w-full justify-start gap-2.5 py-2.5 font-semibold shadow-sm"
      >
        <Plus className="h-4 w-4" />
        <span>New Conversation</span>
      </Button>

      {/* Session Threads List */}
      <div className="mt-4 flex-1 overflow-y-auto pr-1">
        <span className="px-2 text-[10px] font-mono uppercase tracking-wider text-ink-muted">
          Past Sessions
        </span>
        <div className="mt-2 flex flex-col gap-1.5">
          {sessions.length === 0 ? (
            <p className="px-3 py-6 text-center text-xs text-ink-muted">
              No previous threads.
            </p>
          ) : (
            sessions.map((s) => (
              <button
                key={s.session_id}
                type="button"
                onClick={() => onSelect(s.session_id)}
                className={cn(
                  "group flex w-full items-center justify-between rounded-xl px-3 py-2.5 text-left text-xs transition-all",
                  s.session_id === activeSessionId
                    ? "border border-brass/40 bg-brass/10 font-semibold text-ink-primary shadow-xs"
                    : "border border-transparent text-ink-secondary hover:border-surface-border hover:bg-surface-0 hover:text-ink-primary"
                )}
              >
                <div className="flex min-w-0 items-center gap-2">
                  <MessageSquare className="h-3.5 w-3.5 shrink-0 text-brass" />
                  <span className="truncate">{s.title ?? "Mobility Analysis"}</span>
                </div>
                <button
                  type="button"
                  onClick={(e) => onDelete(s.session_id, e)}
                  className="rounded p-1 text-ink-muted opacity-0 transition-opacity hover:text-danger group-hover:opacity-100"
                  aria-label="Delete session"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </button>
            ))
          )}
        </div>
      </div>

      {/* Telemetry Footnote */}
      <div className="mt-auto border-t border-surface-border/80 pt-3 text-[11px] text-ink-muted">
        <div className="flex items-center justify-between">
          <span>Engine</span>
          <span className="font-mono text-ink-primary">PostgreSQL / DuckDB</span>
        </div>
        <div className="flex items-center justify-between mt-1">
          <span>Zones</span>
          <span className="font-mono text-ink-primary">263 NYC TLC</span>
        </div>
      </div>
    </aside>
  );
}

function EmptyState({ onPick }: { onPick: (q: string) => void }) {
  const CATEGORIES = [
    {
      label: "Fare & Surge Models",
      color: "text-brass",
      queries: [
        "What is the average fare from JFK Airport to Midtown?",
        "What drives sudden surge pricing in Zone 161 (Midtown East)?",
      ],
    },
    {
      label: "Demand & Peak Corridors",
      color: "text-emerald-600",
      queries: [
        "Which zone has the highest trip volume on Friday evenings?",
        "How do trip durations compare between FiDi and Williamsburg?",
      ],
    },
    {
      label: "TLC Mart SQL Aggregates",
      color: "text-indigo-600",
      queries: [
        "List top 5 pickup locations ranked by total trips in the database.",
        "Compare borough-level average trip distance for Manhattan.",
      ],
    },
  ];

  return (
    <div className="flex flex-col gap-6 py-4">
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="rounded-3xl border border-surface-border bg-gradient-to-br from-surface-1 via-surface-1 to-surface-0/60 p-6 sm:p-8 shadow-xs"
      >
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-brass text-white shadow-sm">
            <Sparkles className="h-5 w-5" />
          </div>
          <div>
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-brass">
              ATLAS AI Analyst
            </span>
            <h2 className="text-xl font-bold text-ink-primary sm:text-2xl">
              Ask New York City Anything
            </h2>
          </div>
        </div>

        <p className="mt-3 text-xs text-ink-secondary sm:text-sm">
          Natural language interface powered by real TLC database marts (<code className="font-mono text-ink-primary bg-surface-0 px-1 py-0.5 rounded">zone_hourly_demand</code>). Run instant aggregations, examine congestion curves, and inspect compiled SQL.
        </p>

        {/* Categorized Prompt Matrices */}
        <div className="mt-6 grid grid-cols-1 gap-3.5 sm:grid-cols-3">
          {CATEGORIES.map((cat, catIdx) => (
            <div
              key={cat.label}
              className="flex flex-col gap-2 rounded-2xl border border-surface-border/80 bg-surface-1/90 p-4 shadow-xs"
            >
              <span className={`text-[11px] font-mono font-bold uppercase tracking-wider ${cat.color}`}>
                {cat.label}
              </span>
              <div className="flex flex-col gap-2 mt-1">
                {cat.queries.map((q, qIdx) => (
                  <motion.button
                    key={q}
                    initial={{ opacity: 0, y: 4 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.2, delay: (catIdx * 2 + qIdx) * 0.04 }}
                    onClick={() => onPick(q)}
                    className="group text-left rounded-xl border border-surface-border/60 bg-surface-0/60 p-2.5 text-xs text-ink-secondary transition-all hover:border-brass/50 hover:bg-surface-1 hover:text-ink-primary hover:shadow-xs"
                  >
                    <div className="flex items-start gap-2">
                      <Bot className="h-3.5 w-3.5 text-brass shrink-0 mt-0.5 transition-transform group-hover:scale-110" />
                      <span className="leading-snug">{q}</span>
                    </div>
                  </motion.button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </motion.div>
    </div>
  );
}

function TurnBubble({ turn, onPickPrompt }: { turn: Turn; onPickPrompt?: (prompt: string) => void }) {
  const isUser = turn.role === "user";
  const [copied, setCopied] = useState(false);

  function handleCopy() {
    navigator.clipboard.writeText(turn.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  if (isUser) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex justify-end"
      >
        <div className="max-w-[80%] rounded-2xl rounded-tr-xs bg-brass px-5 py-3 text-sm text-white shadow-sm">
          <p className="whitespace-pre-wrap leading-relaxed">{turn.content}</p>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex items-start gap-3.5"
    >
      {/* Avatar */}
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-brass/10 border border-brass/25 text-brass shadow-2xs">
        <Compass className="h-4 w-4" />
      </div>

      {/* Assistant Card */}
      <div className="flex-1 overflow-hidden rounded-2xl rounded-tl-xs border border-surface-border bg-surface-1 p-5 shadow-xs">
        {/* Header Badges */}
        <div className="flex items-center justify-between gap-2 border-b border-surface-border/60 pb-3 mb-3">
          <div className="flex items-center gap-2">
            {turn.modelLabel ? (
              <span className="inline-flex items-center gap-1.5 rounded-full border border-verdigris/25 bg-verdigris/10 px-2.5 py-0.5 text-[11px] font-mono font-semibold text-verdigris">
                {turn.modelLabel}
              </span>
            ) : null}
            {turn.route ? (
              <span className="inline-flex items-center gap-1.5 rounded-full border border-brass/25 bg-brass/10 px-2.5 py-0.5 text-[11px] font-mono font-semibold text-brass">
                {turn.route === "numeric" ? "SQL Query (Mart)" : "Grounded Retrieval"}
              </span>
            ) : turn.pending ? (
              <span className="flex items-center gap-2 font-mono text-xs text-brass">
                <PulsingStatusDot status="live" size={5} />
                <span>ANALYZING TLC MART...</span>
              </span>
            ) : null}
          </div>

          <button
            type="button"
            onClick={handleCopy}
            className="flex items-center gap-1 rounded px-2 py-1 text-xs text-ink-muted transition-colors hover:text-ink-primary"
            title="Copy answer"
          >
            {copied ? <Check className="h-3.5 w-3.5 text-emerald-500" /> : <Copy className="h-3.5 w-3.5" />}
            <span className="text-[10px] uppercase font-mono">{copied ? "Copied" : "Copy"}</span>
          </button>
        </div>

        {/* Content with rich formatting and structured tables */}
        <div className="text-sm text-ink-primary leading-relaxed font-body-md">
          {turn.content ? (
            <>
              <FormattedMessage content={turn.content} onPickPrompt={onPickPrompt} />
              {turn.pending && (
                <span className="ml-1 inline-block animate-pulse font-bold text-brass">▍</span>
              )}
            </>
          ) : turn.pending ? (
            <div className="flex items-center gap-2 py-1 text-xs font-mono text-ink-secondary">
              <PulsingStatusDot status="live" size={6} />
              <span>Querying 1.4B+ TLC trip mart records...</span>
            </div>
          ) : (
            <p className="text-xs text-ink-muted italic">No response returned.</p>
          )}
        </div>

        {/* Collapsible SQL Block */}
        {turn.sql && <SqlBlock sql={turn.sql} />}
      </div>
    </motion.div>
  );
}

function SqlBlock({ sql }: { sql: string }) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  function copySql() {
    navigator.clipboard.writeText(sql);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="mt-4 rounded-xl border border-surface-border/80 bg-surface-0/60 p-3">
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="flex items-center gap-2 font-mono text-xs font-semibold text-brass hover:opacity-80 transition-opacity"
        >
          <Database className="h-3.5 w-3.5" />
          <span>{open ? "Hide Executed SQL" : "Inspect Compiled SQL"}</span>
          {open ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
        </button>

        {open && (
          <button
            type="button"
            onClick={copySql}
            className="flex items-center gap-1 rounded bg-surface-1 px-2 py-0.5 text-[10px] font-mono text-ink-secondary shadow-xs hover:text-ink-primary"
          >
            {copied ? <Check className="h-3 w-3 text-emerald-500" /> : <Copy className="h-3 w-3" />}
            <span>{copied ? "Copied" : "Copy SQL"}</span>
          </button>
        )}
      </div>

      <AnimatePresence>
        {open && (
          <motion.pre
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="mt-3 overflow-x-auto rounded-lg border border-surface-border/60 bg-surface-1 p-3.5 font-mono text-xs text-ink-secondary"
          >
            {sql}
          </motion.pre>
        )}
      </AnimatePresence>
    </div>
  );
}

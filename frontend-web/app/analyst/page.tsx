"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Send, Bot, Sparkles, Database, Plus, Trash2, Square, MessageSquare } from "lucide-react";
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
import { useAppContext } from "@/context/AppContext";
import { useAuth } from "@/context/AuthContext";

interface Turn {
  role: "user" | "assistant";
  content: string;
  route?: ChatRoute | null;
  sql?: string | null;
  pending?: boolean;
}

const EXAMPLE_PROMPTS = [
  "What's the average fare from JFK Airport?",
  "Why is Zone 161 busy at rush hour?",
  "Which zone has the highest demand on weekday evenings?",
  "What drives surge pricing in Manhattan?",
];

const SESSION_KEY = "analyst_session_id";

function looksNumeric(text: string): boolean {
  return /\d/.test(text);
}

export default function AnalystPage() {
  const { selectedCity } = useAppContext();
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
      .catch(() => {}); // history sidebar is a convenience -- a failed refresh just leaves the last-known list
  }, []);

  useEffect(() => {
    if (authLoading || !user) return;
    refreshSessions();
    const saved = localStorage.getItem(SESSION_KEY);
    if (!saved) return;
    setSessionId(saved);
    getChatHistory(saved)
      .then((history) =>
        setTurns(
          history.map((m: ChatMessage) => ({
            role: m.role === "user" ? "user" : "assistant",
            content: m.content,
            route: m.route,
            sql: m.sql,
          }))
        )
      )
      .catch(() => {
        localStorage.removeItem(SESSION_KEY);
        setSessionId(undefined);
      });
  }, [authLoading, user, refreshSessions]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns]);

  useEffect(() => () => closeRef.current?.(), []);

  // Marks the in-progress assistant turn done with whatever content
  // accumulated so far -- used both when the user hits Stop and whenever
  // the stream socket closes without a "done" frame.
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
    setTurns((prev) => [...prev, { role: "user", content: question }, { role: "assistant", content: "", pending: true }]);

    closeRef.current = streamChat(
      { question, session_id: sessionId },
      {
        onFrame: (frame) => {
          if ("error" in frame) {
            setStreaming(false);
            setWsError(frame.error);
            setTurns((prev) => {
              const next = [...prev];
              next[next.length - 1] = { role: "assistant", content: `Error: ${frame.error}` };
              return next;
            });
            return;
          }
          if (frame.type === "chunk") {
            setTurns((prev) => {
              const next = [...prev];
              const last = next[next.length - 1];
              next[next.length - 1] = { ...last, content: last.content + frame.text, pending: true };
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
              };
              return next;
            });
            refreshSessions();
          }
        },
        onError: () => {
          setStreaming(false);
          setWsError("Connection to the analyst backend failed. Is the API running?");
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
    if (!window.confirm("Delete this conversation? This can't be undone.")) return;
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
          {authLoading ? "Checking your session..." : "Redirecting to login..."}
        </p>
      </div>
    );
  }

  return (
    <div className="flex gap-8 h-full">
      <SessionSidebar
        sessions={sessions}
        activeSessionId={sessionId}
        onNewChat={newChat}
        onSelect={selectSession}
        onDelete={handleDeleteSession}
      />

      <div className="flex flex-col gap-12 h-full flex-1 min-w-0">
        {/* Header - only show when no conversation */}
        {turns.length === 0 && (
          <section className="flex flex-col gap-3">
            <span className="font-label-sm text-brass tracking-wider">
              Conversational Intelligence
            </span>
            <h1 className="font-display-lg text-ink-primary">
              Ask the City
            </h1>
            <p className="font-body-md max-w-2xl text-ink-secondary">
              Ask questions about fares, demand, patterns, and mobility trends. Numeric questions are answered with SQL queries; explanatory questions use retrieval-augmented generation.
            </p>
          </section>
        )}

        {/* Chat Area */}
        <div className="flex-1 flex flex-col gap-6 min-h-0">
          {/* Messages Container */}
          <div className="flex-1 overflow-y-auto pr-2">
            {turns.length === 0 ? (
              <EmptyState onPick={ask} />
            ) : (
              <div className="flex flex-col gap-6 py-6">
                <AnimatePresence initial={false}>
                  {turns.map((turn, i) => (
                    <TurnBubble key={i} turn={turn} />
                  ))}
                </AnimatePresence>
                <div ref={bottomRef} />
              </div>
            )}
          </div>

          {/* Error Message */}
          {wsError && (
            <div className="rounded-sm border border-oxide/40 bg-oxide/5 px-4 py-3 font-body-sm text-oxide">
              <p className="font-section-md mb-1">Connection Error</p>
              <p>{wsError}</p>
            </div>
          )}

          {/* Input Form */}
          <form onSubmit={handleSubmit} className="flex gap-3 border-t border-surface-border pt-6">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about fares, demand, or patterns..."
              className="flex-1 bg-surface-1 border-surface-border focus:border-brass/50 transition-colors font-body-md"
              disabled={streaming}
            />
            {streaming ? (
              <Button type="button" variant="secondary" onClick={stopGenerating} className="px-6">
                <Square className="h-4 w-4" />
              </Button>
            ) : (
              <Button type="submit" disabled={!input.trim()} className="px-6">
                <Send className="h-4 w-4" />
              </Button>
            )}
          </form>
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
    <aside className="hidden md:flex w-64 shrink-0 flex-col gap-3 h-full">
      <Button variant="secondary" onClick={onNewChat} className="justify-start gap-2 w-full">
        <Plus className="h-4 w-4" />
        New Chat
      </Button>

      <div className="flex-1 overflow-y-auto flex flex-col gap-1 pr-1">
        {sessions.length === 0 ? (
          <p className="font-body-sm text-ink-secondary px-2 py-4">No past conversations yet.</p>
        ) : (
          sessions.map((s) => (
            <button
              key={s.session_id}
              onClick={() => onSelect(s.session_id)}
              className={cn(
                "group flex items-start gap-2 rounded-sm px-3 py-2.5 text-left transition-colors",
                s.session_id === activeSessionId
                  ? "bg-brass/10 border border-brass/30"
                  : "border border-transparent hover:bg-surface-1"
              )}
            >
              <MessageSquare className="h-4 w-4 mt-0.5 shrink-0 text-ink-secondary" />
              <span className="flex-1 min-w-0">
                <span className="block truncate font-body-sm text-ink-primary">{s.title ?? "New conversation"}</span>
              </span>
              <span
                role="button"
                tabIndex={0}
                onClick={(e) => onDelete(s.session_id, e)}
                className="opacity-0 group-hover:opacity-100 transition-opacity text-ink-secondary hover:text-oxide shrink-0"
                aria-label="Delete conversation"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </span>
            </button>
          ))
        )}
      </div>
    </aside>
  );
}

function EmptyState({ onPick }: { onPick: (q: string) => void }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-8 text-center py-12">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4 }}
        className="flex flex-col items-center gap-4"
      >
        <div className="p-3 bg-brass/10 rounded-sm">
          <Sparkles className="h-8 w-8 text-brass" />
        </div>
        <div>
          <h1 className="font-display-md text-ink-primary">Ask the City</h1>
          <p className="mt-2 max-w-md font-body-md text-ink-secondary">
            Ask questions about mobility patterns, fares, and demand. The system intelligently routes your query to either SQL analysis or retrieval-augmented generation.
          </p>
        </div>
      </motion.div>

      <div className="grid w-full max-w-2xl gap-3 sm:grid-cols-2">
        {EXAMPLE_PROMPTS.map((q, idx) => (
          <motion.button
            key={q}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: idx * 0.06 }}
            onClick={() => onPick(q)}
            className="group relative border border-surface-border bg-surface-1 p-4 text-left font-body-sm text-ink-secondary transition-all hover:border-brass/40 hover:bg-surface-1/80 hover:text-ink-primary rounded-sm"
          >
            <span className="flex items-center gap-3">
              <Bot className="h-4 w-4 text-brass shrink-0 transition-transform group-hover:scale-110" />
              <span>{q}</span>
            </span>
          </motion.button>
        ))}
      </div>
    </div>
  );
}

function TurnBubble({ turn }: { turn: Turn }) {
  const isUser = turn.role === "user";
  const numeric = !isUser && looksNumeric(turn.content);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: "easeOut" }}
      className={cn("flex", isUser ? "justify-end" : "justify-start")}
    >
      <div className={cn("max-w-[75%] rounded-sm px-6 py-4 border", isUser ? "bg-brass text-brass-fg font-body-md border-brass" : "bg-surface-1 border-surface-border text-ink-primary")}>
        {!isUser && (
          <div className="flex items-center gap-2 mb-3">
            {turn.route ? (
              <Badge basis={turn.route === "numeric" ? "computed" : "modeled_estimate"}>
                {turn.route === "numeric" ? "SQL Query" : "Retrieval"}
              </Badge>
            ) : turn.pending ? (
              <span className="flex items-center gap-2 font-label-sm text-brass">
                <PulsingStatusDot status="live" size={5} />
                <span>Analyzing...</span>
              </span>
            ) : null}
          </div>
        )}
        <p className={cn("whitespace-pre-wrap font-body-md leading-relaxed", numeric && "font-mono")}>
          {turn.content}
          {turn.pending && <span className="ml-1 inline-block animate-pulse text-brass font-bold">▍</span>}
        </p>
        {!isUser && turn.sql && <SqlBlock sql={turn.sql} />}
      </div>
    </motion.div>
  );
}

function SqlBlock({ sql }: { sql: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-4 pt-4 border-t border-surface-border/60">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 font-label-sm text-brass hover:opacity-80 transition-opacity"
      >
        <Database className="h-4 w-4" />
        {open ? "Hide" : "Show"} SQL Query
      </button>
      <AnimatePresence>
        {open && (
          <motion.pre
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="mt-3 overflow-x-auto rounded-sm border border-surface-border bg-surface-0 p-4 font-mono text-xs text-ink-secondary"
          >
            {sql}
          </motion.pre>
        )}
      </AnimatePresence>
    </div>
  );
}

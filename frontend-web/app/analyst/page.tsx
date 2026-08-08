"use client";

import { useEffect, useRef, useState } from "react";
import { Send } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { cn } from "@/lib/utils";
import { getChatHistory, streamChat, type ChatMessage, type ChatRoute } from "@/lib/api";

// Local message shape -- superset of ChatMessage so we can track in-flight
// streaming assistant turns before the "done" frame lands.
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

// Numbers/SQL results read as instrument readouts (font-mono), matching
// PredictionField's treatment of numeric data -- a rough heuristic, not a
// parser: any answer containing a digit gets the mono treatment.
function looksNumeric(text: string): boolean {
  return /\d/.test(text);
}

export default function AnalystPage() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string | undefined>(undefined);
  const [wsError, setWsError] = useState<string | null>(null);
  const closeRef = useRef<(() => void) | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Restore session + history on mount, if we have one.
  useEffect(() => {
    const saved = typeof window !== "undefined" ? localStorage.getItem(SESSION_KEY) : null;
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
        // Stale/expired session id -- start fresh silently.
        localStorage.removeItem(SESSION_KEY);
        setSessionId(undefined);
      });
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns]);

  useEffect(() => () => closeRef.current?.(), []);

  function ask(question: string) {
    if (!question.trim()) return;
    setWsError(null);
    setInput("");
    setTurns((prev) => [...prev, { role: "user", content: question }, { role: "assistant", content: "", pending: true }]);

    closeRef.current = streamChat(
      { question, session_id: sessionId },
      {
        onFrame: (frame) => {
          if ("error" in frame) {
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
          }
        },
        onError: () => setWsError("Connection to the analyst backend failed. Is the API running?"),
      }
    );
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    ask(input);
  }

  return (
    <div className="mx-auto flex h-[calc(100vh-9rem)] max-w-3xl flex-col">
      <div className="flex-1 overflow-y-auto pr-1">
        {turns.length === 0 ? (
          <EmptyState onPick={ask} />
        ) : (
          <div className="flex flex-col gap-4 py-4">
            {turns.map((turn, i) => (
              <TurnBubble key={i} turn={turn} />
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {wsError && (
        <div className="mb-2 rounded-xl border border-dashed border-oxide/40 bg-oxide/5 px-3 py-2 text-xs text-oxide">
          {wsError}
        </div>
      )}

      <form onSubmit={handleSubmit} className="flex gap-2 border-t border-surface-border pt-4">
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about fares, demand, or ride patterns..."
          className="flex-1"
        />
        <Button type="submit" disabled={!input.trim()}>
          <Send className="h-4 w-4" />
        </Button>
      </form>
    </div>
  );
}

function EmptyState({ onPick }: { onPick: (q: string) => void }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-6 text-center">
      <div>
        <h1 className="font-display text-2xl text-ink-primary">AI Analyst</h1>
        <p className="mt-1 text-sm text-ink-muted">
          Ask a question -- numeric questions route to SQL against the trip warehouse, explanatory
          questions route to retrieval over generated insight docs.
        </p>
      </div>
      <div className="grid w-full max-w-lg gap-2 sm:grid-cols-2">
        {EXAMPLE_PROMPTS.map((q) => (
          <button
            key={q}
            onClick={() => onPick(q)}
            className="rounded-xl border border-surface-border bg-surface-0 px-3 py-2 text-left text-sm text-ink-secondary transition-colors hover:border-brass/40 hover:text-ink-primary"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}

function TurnBubble({ turn }: { turn: Turn }) {
  const isUser = turn.role === "user";
  const numeric = !isUser && looksNumeric(turn.content);

  return (
    <div className={cn("flex", isUser ? "justify-end" : "justify-start")}>
      <div className={cn("max-w-[85%] rounded-2xl px-4 py-2.5", isUser ? "bg-accent text-accent-fg" : "bg-surface-2 text-ink-primary")}>
        {!isUser && turn.route && (
          <Badge basis={turn.route === "sql" ? "computed" : "modeled_estimate"} className="mb-1.5">
            {turn.route === "sql" ? "SQL grounded" : "retrieval"}
          </Badge>
        )}
        <p className={cn("whitespace-pre-wrap text-sm", numeric && "font-mono")}>
          {turn.content}
          {turn.pending && <span className="ml-0.5 animate-pulse">▍</span>}
        </p>
        {!isUser && turn.sql && <SqlBlock sql={turn.sql} />}
      </div>
    </div>
  );
}

function SqlBlock({ sql }: { sql: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-2">
      <button
        onClick={() => setOpen((v) => !v)}
        className="text-xs uppercase tracking-wider text-brass hover:opacity-80"
      >
        {open ? "Hide" : "Show"} generated SQL
      </button>
      {open && (
        <pre className="mt-1.5 overflow-x-auto rounded-lg border border-surface-border bg-surface-0 p-3 font-mono text-xs text-ink-secondary">
          {sql}
        </pre>
      )}
    </div>
  );
}

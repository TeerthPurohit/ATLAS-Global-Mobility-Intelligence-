import React, { useState, useEffect, useRef } from "react";
import { sendChatMessage, ChatMessage } from "../api/client";
import { Sparkles, Send, Terminal, RefreshCw, MessageSquare, Database, Server } from "lucide-react";

function sqlTableName(sql: string): string {
  const match = sql.match(/from\s+"?(\w+)"?/i);
  return match ? match[1] : "unknown";
}

// Numeric answers come pre-formatted as "Based on the marts:\n- Label: value" lines
// (see rag_pipeline.py::_format_numeric_answer) -- render those as label/value rows
// instead of a raw text blob.
function renderAnswer(content: string) {
  const lines = content.split("\n");
  return lines.map((line, i) => {
    const bullet = line.match(/^-\s*(.+?):\s*(.+)$/);
    if (!bullet) return <div key={i}>{line}</div>;
    const [, label, value] = bullet;
    return (
      <div key={i} className="flex items-baseline justify-between gap-4 py-0.5">
        <span className="text-slate-400">{label}</span>
        <span className="font-mono text-slate-100 text-right">{value}</span>
      </div>
    );
  });
}

const SUGGESTED_QUESTIONS = [
  "What is the average fare for trips picked up in JFK Airport?",
  "Why is JFK Airport such an important hub in the network?",
  "Which 5 zones recorded the highest trip demand?",
  "Why does Times Square experience peak demand during evening hours?",
];

export const AIAnalyst: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputQuestion, setInputQuestion] = useState<string>("");
  const [sessionId, setSessionId] = useState<string | undefined>(undefined);
  const [loading, setLoading] = useState<boolean>(false);
  const [openSqlIndex, setOpenSqlIndex] = useState<number | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSend = async (questionText?: string) => {
    const q = questionText || inputQuestion;
    if (!q.trim() || loading) return;

    setInputQuestion("");
    const userMsg: ChatMessage = { role: "user", content: q, timestamp: new Date().toISOString() };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const res = await sendChatMessage(q, sessionId);
      if (!sessionId) {
        setSessionId(res.session_id);
      }
      const assistantMsg: ChatMessage = {
        role: "assistant",
        content: res.answer,
        route: res.route,
        sql: res.sql,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      console.error(err);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Awaiting backend response... Please verify that the FastAPI backend server is online at http://localhost:8000.",
          timestamp: new Date().toISOString(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-[calc(100vh-4rem)] flex flex-col bg-slate-950 max-w-6xl mx-auto p-4 sm:p-6">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-4 shrink-0">
        <div>
          <h1 className="text-lg font-bold text-slate-100 flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-brand-400" />
            Hybrid RAG AI Analyst
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Routes numeric questions to DuckDB SQL Agent and explanatory questions to Qdrant Vector Search
          </p>
        </div>
        {sessionId && (
          <div className="text-[11px] font-mono text-slate-400 bg-slate-900 border border-slate-800 px-3 py-1 rounded-full flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span>Session: {sessionId.slice(0, 8)}...</span>
          </div>
        )}
      </div>

      {/* Message Feed */}
      <div className="flex-1 overflow-y-auto py-4 space-y-4 pr-2">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-6 space-y-4">
            <div className="p-4 rounded-2xl bg-slate-900 border border-slate-800 text-brand-400">
              <MessageSquare className="w-8 h-8" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-slate-200">Ask the TLC Intelligence Analyst</h3>
              <p className="text-xs text-slate-400 mt-1 max-w-md">
                Every number in the response is grounded by real SQL queries or traceable insight vector documents.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-xl text-left mt-4">
              {SUGGESTED_QUESTIONS.map((sq, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSend(sq)}
                  className="p-3 rounded-xl bg-slate-900 border border-slate-800 hover:border-brand-500/40 text-xs text-slate-300 hover:text-white transition-all text-left"
                >
                  "{sq}"
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div
              key={idx}
              className={`flex flex-col ${msg.role === "user" ? "items-end" : "items-start"}`}
            >
              <div
                className={`max-w-2xl rounded-2xl p-4 text-xs leading-relaxed space-y-2 ${
                  msg.role === "user"
                    ? "bg-brand-500 text-slate-950 rounded-br-none"
                    : "bg-slate-900 border border-slate-800 text-slate-200 rounded-bl-none shadow-lg"
                }`}
              >
                {msg.role === "assistant" && msg.route && (
                  <div className="flex items-center justify-between border-b border-slate-800 pb-2 mb-2">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold uppercase tracking-wider ${
                        msg.route === "numeric"
                          ? "bg-indigo-500/20 text-indigo-400 border border-indigo-500/30"
                          : "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                      }`}
                    >
                      {msg.route === "numeric" ? "NL-to-SQL Path (DuckDB)" : "Vector Retrieval Path (Qdrant)"}
                    </span>
                    <span className="text-[10px] font-mono text-slate-400">
                      Provenance: {msg.route === "numeric" ? "DuckDB Mart" : "Vector Collection"}
                    </span>
                  </div>
                )}

                <div className="whitespace-pre-wrap">{renderAnswer(msg.content)}</div>

                {/* Collapsible SQL Query Box */}
                {msg.sql && (
                  <div className="mt-3 pt-2 border-t border-slate-800">
                    <button
                      onClick={() => setOpenSqlIndex(openSqlIndex === idx ? null : idx)}
                      className="flex items-center space-x-1.5 text-[11px] text-brand-400 font-mono hover:underline"
                    >
                      <Terminal className="w-3.5 h-3.5" />
                      <span>{openSqlIndex === idx ? "Hide Executed SQL" : "Show Executed SQL Query"}</span>
                    </button>
                    {openSqlIndex === idx && (
                      <div className="mt-2 space-y-1">
                        <pre className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-[11px] font-mono text-emerald-400 overflow-x-auto whitespace-pre-wrap">
                          {msg.sql}
                        </pre>
                        <div className="text-[10px] font-mono text-slate-500 text-right">
                          Engine: DuckDB · Table: {sqlTableName(msg.sql)}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
              <span className="text-[10px] text-slate-500 mt-1 px-1 font-mono">
                {new Date(msg.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
              </span>
            </div>
          ))
        )}

        {loading && (
          <div className="flex items-center space-x-2 p-4 rounded-2xl bg-slate-900 border border-slate-800 text-xs text-slate-400 w-fit font-mono">
            <RefreshCw className="w-4 h-4 text-brand-400 animate-spin" />
            <span>Analyzing query & executing RAG pipeline...</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Bar */}
      <div className="pt-3 border-t border-slate-800 shrink-0 space-y-2">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex items-center space-x-2"
        >
          <input
            type="text"
            value={inputQuestion}
            onChange={(e) => setInputQuestion(e.target.value)}
            placeholder="Ask a question (e.g. 'Average fare in JFK' or 'Why is zone 161 busy')..."
            className="flex-1 bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-brand-500"
          />
          <button
            type="submit"
            disabled={loading || !inputQuestion.trim()}
            className="p-3 rounded-xl bg-brand-500 hover:bg-brand-400 disabled:opacity-50 text-slate-950 font-semibold shadow-lg shadow-brand-500/20 transition-all"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>

        <div className="flex items-center justify-between text-[10px] font-mono text-slate-500 px-1">
          <span>Routing Engine: Intent Router (sql_agent.py vs vector_search)</span>
          <span>Zero Fabricated Metrics Policy Enforced</span>
        </div>
      </div>
    </div>
  );
};

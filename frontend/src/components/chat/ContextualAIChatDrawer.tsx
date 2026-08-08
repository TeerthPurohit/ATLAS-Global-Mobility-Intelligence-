import React, { useState, useEffect, useRef } from "react";
import { Area, ChatMessage, sendCityChatMessage, sendChatMessage } from "../../api/client";
import { X, Send, Bot, Sparkles, Code2, Database, MapPin, Globe, RefreshCw, MessageSquare } from "lucide-react";
import { Provenance } from "../ui/Provenance";

interface ContextualAIChatDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  cityId: string;
  cityName?: string;
  selectedArea?: Area | null;
  initialQuestion?: string;
}

export const ContextualAIChatDrawer: React.FC<ContextualAIChatDrawerProps> = ({
  isOpen,
  onClose,
  cityId,
  cityName = "New York City",
  selectedArea,
  initialQuestion,
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content: `Hello! I am your AI Mobility Analyst for ${cityName}. How can I help you analyze demand, fares, or spatial patterns today?`,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    },
  ]);
  const [inputQuestion, setInputQuestion] = useState("");
  const [sessionId, setSessionId] = useState<string | undefined>(undefined);
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const SUGGESTED_PROMPTS = [
    `What's the busiest area in ${cityName} right now?`,
    selectedArea ? `Why is demand higher in ${selectedArea.name}?` : "Show me the highest fare areas.",
    `What will demand look like tomorrow morning in ${cityName}?`,
    "Compare Manhattan and Brooklyn average fares.",
  ];

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => {
    if (initialQuestion && isOpen) {
      handleSend(initialQuestion);
    }
  }, [initialQuestion, isOpen]);

  const handleSend = async (questionText: string) => {
    if (!questionText.trim() || loading) return;

    const userMsg: ChatMessage = {
      role: "user",
      content: questionText,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputQuestion("");
    setLoading(true);

    try {
      // Send city-scoped chat message with area context
      let res;
      try {
        res = await sendCityChatMessage(cityId, questionText, selectedArea?.area_id, sessionId);
      } catch (e) {
        // Fallback to global sendChatMessage
        res = await sendChatMessage(questionText, sessionId);
      }

      if (res.session_id) setSessionId(res.session_id);

      const assistantMsg: ChatMessage = {
        role: "assistant",
        content: res.answer,
        route: res.route,
        sql: res.sql,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      console.error(err);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Sorry, I encountered an issue querying the RAG analytics engine. Please ensure backend services are running.",
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-y-0 right-0 z-[1500] w-full sm:w-[480px] bg-slate-900 border-l border-slate-800 shadow-2xl flex flex-col justify-between font-sans select-none animate-slideInRight">
      {/* Drawer Header */}
      <div className="p-4 border-b border-slate-800 bg-slate-950/80 backdrop-blur-md flex items-center justify-between">
        <div className="flex items-center space-x-2.5">
          <div className="w-8 h-8 rounded-lg bg-brand-500 flex items-center justify-center text-slate-950 font-bold shadow-md shadow-brand-500/30">
            <Bot className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="text-sm font-bold text-slate-100">AI Mobility Assistant</h3>
              <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                Hybrid RAG
              </span>
            </div>
            <p className="text-[11px] font-mono text-slate-400">
              Bound Context: <span className="text-brand-400 font-semibold">{cityName}</span>
              {selectedArea && ` • #${selectedArea.area_id} (${selectedArea.name})`}
            </p>
          </div>
        </div>

        <button
          onClick={onClose}
          className="p-1 rounded-md text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Chat Messages Body */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-950/60">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex flex-col ${msg.role === "user" ? "items-end" : "items-start"}`}
          >
            <div className="flex items-center space-x-1.5 mb-1 text-[10px] text-slate-500 font-mono">
              <span>{msg.role === "user" ? "You" : "Mobility AI"}</span>
              <span>•</span>
              <span>{msg.timestamp}</span>
              {msg.route && (
                <span className="px-1.5 py-0.2 rounded bg-slate-800 text-brand-400 border border-slate-700">
                  {msg.route}
                </span>
              )}
            </div>

            <div
              className={`p-3.5 rounded-2xl max-w-[90%] text-xs leading-relaxed ${
                msg.role === "user"
                  ? "bg-brand-500 text-slate-950 font-semibold rounded-tr-none shadow-md shadow-brand-500/20"
                  : "bg-slate-900 border border-slate-800 text-slate-200 rounded-tl-none shadow-md"
              }`}
            >
              {msg.content}

              {/* Display SQL Query metadata if generated by QueryPlan */}
              {msg.sql && (
                <div className="mt-2.5 pt-2 border-t border-slate-800 font-mono text-[10px] bg-slate-950 p-2 rounded-lg border text-emerald-400 overflow-x-auto">
                  <div className="flex items-center space-x-1 text-slate-400 mb-1">
                    <Code2 className="w-3 h-3 text-emerald-400" />
                    <span className="font-semibold text-slate-300">Deterministic DuckDB Query</span>
                  </div>
                  <code>{msg.sql}</code>
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex items-center space-x-2 text-xs text-brand-400 font-mono p-3 bg-slate-900/60 border border-slate-800 rounded-xl animate-pulse">
            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            <span>Analyzing spatial data & compiling NL-to-SQL query plan...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Contextual Suggested Prompts */}
      <div className="p-3 bg-slate-900 border-t border-slate-800 space-y-2">
        <p className="text-[10px] font-mono text-slate-400 uppercase font-semibold">Suggested Questions</p>
        <div className="flex flex-wrap gap-1.5">
          {SUGGESTED_PROMPTS.map((prompt, idx) => (
            <button
              key={idx}
              onClick={() => handleSend(prompt)}
              className="text-[11px] px-2.5 py-1 rounded-lg bg-slate-950 border border-slate-800 hover:border-brand-500/40 hover:text-brand-300 text-slate-300 transition-colors text-left font-sans"
            >
              {prompt}
            </button>
          ))}
        </div>
      </div>

      {/* Input Box */}
      <div className="p-3 bg-slate-950 border-t border-slate-800">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend(inputQuestion);
          }}
          className="flex items-center space-x-2"
        >
          <input
            type="text"
            value={inputQuestion}
            onChange={(e) => setInputQuestion(e.target.value)}
            placeholder={`Ask AI about ${selectedArea ? selectedArea.name : cityName}...`}
            className="flex-1 py-2.5 px-3.5 bg-slate-900 border border-slate-800 rounded-xl text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-brand-500/40 font-sans"
          />
          <button
            type="submit"
            disabled={!inputQuestion.trim() || loading}
            className="p-2.5 rounded-xl bg-brand-500 hover:bg-brand-400 disabled:opacity-50 text-slate-950 font-bold transition-all shadow-md"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
};

"use client";
import { Sparkles, Plus, Circle } from "lucide-react";

export default function Sidebar({
  mode, onNewSession, sessionId,
}: { mode: string | null; onNewSession: () => void; sessionId: string | null }) {
  return (
    <aside className="sidebar">
      <div className="px-4 py-5 flex items-center gap-3 border-b border-border">
        <span className="brand-mark"><Sparkles size={20} /></span>
        <div><span className="font-semibold text-slate-100 text-base">SyncFlow AI</span><div className="eyebrow">CONTROL CENTER</div></div>
      </div>

      <div className="px-3 py-3">
        <button
          onClick={onNewSession}
          className="w-full flex items-center justify-center gap-1.5 text-xs px-3 py-2.5 rounded-lg bg-accent text-white font-semibold shadow-lg shadow-violet-500/10 hover:brightness-110"
        >
          <Plus size={13} /> New execution
        </button>
      </div>

      <div className="px-4 py-2 text-[11px] uppercase tracking-wide text-slate-600">Active session</div>
      <div className="px-3">
        {sessionId ? (
          <div className="flex items-center gap-2 text-xs text-slate-300 bg-bg-elevated border border-border rounded-lg px-2.5 py-2">
            <Circle size={8} className="text-accent fill-accent" />
            <span className="truncate">{sessionId}</span>
          </div>
        ) : (
          <div className="text-xs text-slate-600 px-1">No active session</div>
        )}
      </div>

      <div className="engine-mode mt-auto px-4 py-3 border-t border-border text-[11px] text-slate-600">
        Engine mode:{" "}
        <span className={mode === "llm" ? "text-emerald-400" : "text-amber-400"}>
          {mode === "llm" ? "Live LLM" : mode === null ? "…" : "Deterministic demo"}
        </span>
      </div>
    </aside>
  );
}

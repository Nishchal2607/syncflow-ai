"use client";
import { useState } from "react";
import { Sparkles, ArrowRight, Loader2 } from "lucide-react";

const EXAMPLES = [
  "Research three electric vehicle companies, compare their products, verify important claims, and prepare a report.",
  "Research two cloud database providers, compare pricing and reliability, verify claims, and summarize.",
  "Research three renewable energy startups, compare their technology, verify key claims, and write a brief.",
];

export default function GoalInput({ onSubmit }: { onSubmit: (goal: string) => void }) {
  const [goal, setGoal] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const submit = (g: string) => {
    if (!g.trim() || submitting) return;
    setSubmitting(true);
    onSubmit(g.trim());
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-6">
      <div className="w-full max-w-2xl">
        <div className="flex items-center gap-2 mb-2 text-accent">
          <Sparkles size={20} />
          <span className="text-sm font-semibold tracking-wide uppercase">SyncFlow AI</span>
        </div>
        <h1 className="text-2xl font-semibold text-slate-100 mb-1">
          Beyond prompt-and-wait
        </h1>
        <p className="text-sm text-slate-500 mb-6">
          Submit a complex goal. Watch the plan unfold. Pause, redirect, or approve at any point.
        </p>

        <div className="bg-bg-panel border border-border rounded-xl2 p-4 shadow-xl">
          <textarea
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            placeholder="Describe a complex multi-step goal..."
            className="w-full h-24 bg-transparent outline-none resize-none text-sm text-slate-100 placeholder:text-slate-600"
          />
          <div className="flex justify-end">
            <button
              onClick={() => submit(goal)}
              disabled={!goal.trim() || submitting}
              className="flex items-center gap-1.5 text-sm px-4 py-2 rounded-lg bg-accent text-black font-medium disabled:opacity-40"
            >
              {submitting ? <Loader2 size={14} className="animate-spin" /> : <ArrowRight size={14} />}
              Start execution
            </button>
          </div>
        </div>

        <div className="mt-5 space-y-2">
          <div className="text-xs uppercase tracking-wide text-slate-600">Example goals</div>
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              onClick={() => submit(ex)}
              className="block w-full text-left text-xs text-slate-400 hover:text-cyan-300 hover:border-accent border border-border rounded-lg px-3 py-2 bg-bg-elevated transition-colors"
            >
              {ex}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

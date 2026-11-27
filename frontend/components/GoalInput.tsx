"use client";
import { useState } from "react";
import { Sparkles, ArrowRight, Loader2 } from "lucide-react";

const EXAMPLES = [
  "Research three electric vehicle companies, compare their products, verify important claims, and prepare a report.",
  "Research two cloud database providers, compare pricing and reliability, verify claims, and summarize.",
  "Research three renewable energy startups, compare their technology, verify key claims, and write a brief.",
];

export default function GoalInput({ onSubmit }: { onSubmit: (goal: string) => Promise<void> | void }) {
  const [goal, setGoal] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const [error, setError] = useState<string | null>(null);

  const submit = async (g: string) => {
    if (!g.trim() || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      await onSubmit(g.trim());
    } catch (e) {
      setError("Couldn't start the session. Is the backend running?");
      setSubmitting(false);
    }
  };

  return (
    <div className="goal-screen flex items-center justify-center px-6 py-12">
      <div className="w-full max-w-2xl">
        <div className="inline-flex items-center gap-2 mb-5 rounded-full border border-violet-400/20 bg-violet-400/[0.07] px-3 py-1.5 text-violet-300">
          <Sparkles size={15} />
          <span className="text-xs font-semibold tracking-wide">SyncFlow AI</span>
        </div>
        <h1 className="text-4xl font-semibold tracking-tight text-slate-100 mb-1">
          Orchestrate with confidence.
        </h1>
        <p className="text-sm text-slate-500 mb-6">
          Submit a complex goal. Watch the plan unfold. Pause, redirect, or approve at any point.
        </p>

        <div className="goal-composer bg-bg-panel border border-border rounded-xl2 p-5 shadow-xl">
          <textarea
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            placeholder="Describe a complex multi-step goal..."
            className="w-full h-32 bg-transparent outline-none resize-none text-sm text-slate-100 placeholder:text-slate-600"
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

        {error && <div className="mt-3 text-xs text-rose-300 bg-rose-500/10 border border-rose-900/50 rounded-lg px-3 py-2">{error}</div>}
        <div className="mt-5 space-y-2">
          <div className="text-xs uppercase tracking-wide text-slate-600">Example goals</div>
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              disabled={submitting}
              onClick={() => submit(ex)}
              className="block w-full text-left text-xs text-slate-400 hover:text-violet-200 hover:border-violet-400/40 border border-border rounded-xl px-3.5 py-3 bg-bg-elevated/80 transition-colors"
            >
              {ex}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

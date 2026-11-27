"use client";
import { useState } from "react";
import { Sparkles, ArrowRight, Loader2 } from "lucide-react";

const EXAMPLES = [
  "Research three electric vehicle companies, compare their products, verify important claims, and prepare a report.",
  "Research two cloud database providers, compare pricing and reliability, verify claims, and summarize.",
  "Research three renewable energy startups, compare their technology, verify key claims, and write a brief.",
];

<<<<<<< HEAD
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
=======
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
>>>>>>> ff3b8e6d1f4bd3c8d0eb54f5fb1847df4306cdb3
      <div className="w-full max-w-2xl">
        <div className="flex items-center gap-2 mb-2 text-accent">
          <Sparkles size={20} />
          <span className="text-sm font-semibold tracking-wide uppercase">SyncFlow AI</span>
        </div>
<<<<<<< HEAD
        <h1 className="text-4xl font-semibold tracking-tight text-slate-100 mb-1">
          Orchestrate with confidence.
=======
        <h1 className="text-2xl font-semibold text-slate-100 mb-1">
          Beyond prompt-and-wait
>>>>>>> ff3b8e6d1f4bd3c8d0eb54f5fb1847df4306cdb3
        </h1>
        <p className="text-sm text-slate-500 mb-6">
          Submit a complex goal. Watch the plan unfold. Pause, redirect, or approve at any point.
        </p>

<<<<<<< HEAD
        <div className="goal-composer bg-bg-panel border border-border rounded-xl2 p-5 shadow-xl">
=======
        <div className="bg-bg-panel border border-border rounded-xl2 p-4 shadow-xl">
>>>>>>> ff3b8e6d1f4bd3c8d0eb54f5fb1847df4306cdb3
          <textarea
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            placeholder="Describe a complex multi-step goal..."
<<<<<<< HEAD
            className="w-full h-32 bg-transparent outline-none resize-none text-sm text-slate-100 placeholder:text-slate-600"
=======
            className="w-full h-24 bg-transparent outline-none resize-none text-sm text-slate-100 placeholder:text-slate-600"
>>>>>>> ff3b8e6d1f4bd3c8d0eb54f5fb1847df4306cdb3
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

<<<<<<< HEAD
        {error && <div className="mt-3 text-xs text-rose-300 bg-rose-500/10 border border-rose-900/50 rounded-lg px-3 py-2">{error}</div>}

=======
>>>>>>> ff3b8e6d1f4bd3c8d0eb54f5fb1847df4306cdb3
        <div className="mt-5 space-y-2">
          <div className="text-xs uppercase tracking-wide text-slate-600">Example goals</div>
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
<<<<<<< HEAD
              disabled={submitting}
=======
>>>>>>> ff3b8e6d1f4bd3c8d0eb54f5fb1847df4306cdb3
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

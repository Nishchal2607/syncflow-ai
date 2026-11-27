"use client";
import { useState } from "react";
import { SessionStatus } from "@/types";
import { Pause, Play, Rewind, XCircle, Loader2 } from "lucide-react";

const STATUS_STYLE: Record<SessionStatus, string> = {
  IDLE: "bg-slate-700/40 text-slate-300",
  PLANNING: "bg-blue-500/20 text-blue-300",
  RUNNING: "bg-cyan-500/20 text-cyan-300",
  PAUSED: "bg-amber-500/20 text-amber-300",
  AWAITING_APPROVAL: "bg-fuchsia-500/20 text-fuchsia-300",
  COMPLETED: "bg-emerald-500/20 text-emerald-300",
  FAILED: "bg-rose-500/20 text-rose-300",
  CANCELLED: "bg-slate-600/30 text-slate-400",
};

export default function ControlBar({
  goal, status, onPause, onResume, onRedirect, onCancel, busy,
}: {
  goal: string;
  status: SessionStatus;
  onPause: () => void;
  onResume: () => void;
  onRedirect: (instruction: string) => void;
  onCancel: () => void;
  busy: boolean;
}) {
  const [redirecting, setRedirecting] = useState(false);
  const [instruction, setInstruction] = useState("");

  const canPause = status === "RUNNING";
  const canResume = status === "PAUSED";
  const canRedirect = status === "PAUSED";
  const canCancel = !["COMPLETED", "FAILED", "CANCELLED"].includes(status);

  return (
    <div className="control-bar panel">
      <div className="flex-1 min-w-0">
        <div className="text-[11px] uppercase tracking-wide text-slate-500">Goal</div>
        <div className="text-sm text-slate-200 break-words">{goal}</div>
      </div>

      <span className={`text-xs font-medium px-2.5 py-1 rounded-full whitespace-nowrap ${STATUS_STYLE[status]}`}>
        {busy && <Loader2 size={11} className="inline mr-1 animate-spin" />}
        {status.replace(/_/g, " ")}
      </span>

      <div className="intervention-buttons flex flex-wrap items-center gap-2">
        <button
          disabled={!canPause || busy}
          onClick={onPause}
          className="flex items-center gap-1 text-xs px-3 py-1.5 rounded-lg border border-border bg-bg-elevated disabled:opacity-30 hover:border-accent transition-colors"
        >
          <Pause size={13} /> Pause
        </button>
        <button
          disabled={!canResume || busy}
          onClick={onResume}
          className="flex items-center gap-1 text-xs px-3 py-1.5 rounded-lg border border-border bg-bg-elevated disabled:opacity-30 hover:border-accent transition-colors"
        >
          <Play size={13} /> Resume
        </button>
        <button
          disabled={!canRedirect || busy}
          onClick={() => setRedirecting(true)}
          className="flex items-center gap-1 text-xs px-3 py-1.5 rounded-lg border border-border bg-bg-elevated disabled:opacity-30 hover:border-accent transition-colors"
        >
          <Rewind size={13} /> Redirect
        </button>
        <button
          disabled={!canCancel || busy}
          onClick={onCancel}
          className="flex items-center gap-1 text-xs px-3 py-1.5 rounded-lg border border-rose-900/50 text-rose-300 bg-rose-500/5 disabled:opacity-30 hover:border-rose-500 transition-colors"
        >
          <XCircle size={13} /> Cancel
        </button>
      </div>

      {redirecting && (
        <div className="fixed inset-0 p-4 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-bg-panel border border-border rounded-xl2 p-5 w-full max-w-[440px] shadow-2xl">
            <div className="text-sm font-medium mb-1">Redirect execution</div>
            <div className="text-xs text-slate-500 mb-3">
              Describe how to change the current/next task. The backend will update the task graph.
            </div>
            <textarea
              autoFocus
              value={instruction}
              onChange={(e) => setInstruction(e.target.value)}
              placeholder='e.g. "Exclude Company C and research Company D instead"'
              className="w-full h-20 bg-bg-elevated border border-border rounded-lg p-2 text-sm outline-none focus:border-accent resize-none"
            />
            <div className="flex justify-end gap-2 mt-3">
              <button
                onClick={() => { setRedirecting(false); setInstruction(""); }}
                className="text-xs px-3 py-1.5 rounded-lg border border-border"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  if (instruction.trim()) {
                    onRedirect(instruction.trim());
                    setRedirecting(false);
                    setInstruction("");
                  }
                }}
                className="text-xs px-3 py-1.5 rounded-lg bg-accent text-black font-medium"
              >
                Apply redirect
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

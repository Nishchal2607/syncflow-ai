"use client";
import { useState } from "react";
import { Approval } from "@/types";
import { ShieldAlert, Check, X } from "lucide-react";

export default function ApprovalModal({
  approval, onApprove, onReject, busy = false,
}: { approval: Approval; onApprove: () => void; onReject: (feedback: string) => void; busy?: boolean }) {
  const [feedback, setFeedback] = useState("");
  return (
    <div className="fixed inset-0 p-4 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="bg-bg-panel border border-fuchsia-500/30 rounded-xl2 p-5 w-full max-w-[520px] max-h-[90vh] overflow-y-auto shadow-2xl">
        <div className="flex items-center gap-2 mb-3 text-fuchsia-300">
          <ShieldAlert size={18} />
          <div className="text-sm font-semibold">Human approval required</div>
        </div>

        <div className="text-xs uppercase tracking-wide text-slate-500 mb-1">Proposed action</div>
        <div className="text-sm text-slate-100 mb-3">{approval.proposed_action}</div>

        <div className="text-xs uppercase tracking-wide text-slate-500 mb-1">Expected impact</div>
        <div className="text-sm text-slate-300 mb-3">{approval.expected_impact}</div>

        {approval.evidence && approval.evidence.length > 0 && (
          <div className="mb-4">
            <div className="text-xs uppercase tracking-wide text-slate-500 mb-1">Supporting evidence</div>
            <ul className="space-y-1">
              {approval.evidence.map((e, i) => (
                <li key={i} className="text-xs text-slate-400 bg-bg-elevated border border-border rounded-md px-2 py-1">
                  {String(e)}
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="mb-4">
          <div className="text-xs uppercase tracking-wide text-slate-500 mb-1">Revision feedback (used when rejecting)</div>
          <textarea
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            placeholder="Describe what to correct before reapproval..."
            className="w-full h-20 bg-bg-elevated border border-border rounded-lg p-2 text-sm outline-none focus:border-accent resize-none"
          />
        </div>

        <div className="flex justify-end gap-2">
          <button
            disabled={busy}
            onClick={() => onReject(feedback)}
            className="flex items-center gap-1 text-xs px-3 py-1.5 rounded-lg border border-rose-900/50 text-rose-300 bg-rose-500/5 hover:border-rose-500 disabled:opacity-40"
          >
            <X size={13} /> Reject
          </button>
          <button
            disabled={busy}
            onClick={onApprove}
            className="flex items-center gap-1 text-xs px-3 py-1.5 rounded-lg bg-emerald-500 text-black font-medium disabled:opacity-40"
          >
            <Check size={13} /> Approve
          </button>
        </div>
      </div>
    </div>
  );
}

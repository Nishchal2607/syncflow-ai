"use client";
import { EventItem } from "@/types";
import { Activity } from "lucide-react";

const LABELS: Record<string, string> = {
  session_created: "Session created",
  plan_generation_started: "Planner started",
  plan_generated: "Plan generated",
  task_started: "Task started",
  task_completed: "Task completed",
  task_failed: "Task failed",
  agent_paused: "Paused by human",
  human_redirected: "Human redirected execution",
  approval_requested: "Approval requested",
  approval_granted: "Approval granted",
  approval_rejected: "Approval rejected",
  agent_resumed: "Resumed by human",
  session_completed: "Session completed",
  session_cancelled: "Session cancelled",
  session_failed: "Session failed",
};

export default function EventTimeline({ events }: { events: EventItem[] }) {
  const ordered = [...events].reverse();
  return (
    <div className="h-full flex flex-col">
      <div className="px-4 py-2 border-b border-border flex items-center gap-2 text-xs uppercase tracking-wide text-slate-500">
        <Activity size={13} /> Event history
      </div>
      <div className="flex-1 overflow-y-auto px-4 py-2 space-y-1.5">
        {ordered.length === 0 && (
          <div className="text-xs text-slate-600">No events yet.</div>
        )}
        {ordered.map((e) => (
          <div key={e.id} className="flex items-center gap-3 text-xs">
            <span className="text-slate-600 w-20 shrink-0 tabular-nums">
              {new Date(e.timestamp).toLocaleTimeString([], { hour12: false })}
            </span>
            <span className="w-24 shrink-0 text-slate-500">{e.actor}</span>
            <span className="text-slate-200">{LABELS[e.event_type] || e.event_type}</span>
            {e.details?.instruction && (
              <span className="text-cyan-400/80 italic">&ldquo;{e.details.instruction}&rdquo;</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

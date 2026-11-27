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

<<<<<<< HEAD
// Backend REST timestamps can be naive UTC (no "Z"); treat them as UTC, not local time.
const parseTs = (ts: string) => new Date(/([zZ]|[+-]\d{2}:?\d{2})$/.test(ts) ? ts : `${ts}Z`);

const dotColor = (t: string) =>
  /failed|rejected|cancelled/.test(t) ? "#fb7185"
  : /completed|granted/.test(t) ? "#34d399"
  : /approval|paused|redirect/.test(t) ? "#fbbf24"
  : "#38bdf8";

=======
>>>>>>> ff3b8e6d1f4bd3c8d0eb54f5fb1847df4306cdb3
export default function EventTimeline({ events }: { events: EventItem[] }) {
  const ordered = [...events].reverse();
  return (
    <div className="h-full flex flex-col">
<<<<<<< HEAD
      <div className="panel-heading flex items-center gap-2">
        <Activity size={13} /> Live activity <span className="event-count">{events.length} events</span>
=======
      <div className="px-4 py-2 border-b border-border flex items-center gap-2 text-xs uppercase tracking-wide text-slate-500">
        <Activity size={13} /> Event history
>>>>>>> ff3b8e6d1f4bd3c8d0eb54f5fb1847df4306cdb3
      </div>
      <div className="flex-1 overflow-y-auto px-4 py-2 space-y-1.5">
        {ordered.length === 0 && (
          <div className="text-xs text-slate-600">No events yet.</div>
        )}
        {ordered.map((e) => (
<<<<<<< HEAD
          <div key={e.id} className="event-row">
            <span className="text-slate-400 tabular-nums">
              {parseTs(e.timestamp).toLocaleTimeString([], { hour12: false })}
            </span>
            <span className="text-slate-400 break-words">{e.actor}</span>
            <span className="event-description text-slate-200"><i style={{ background: dotColor(e.event_type) }} />{LABELS[e.event_type] || e.event_type}</span>
=======
          <div key={e.id} className="flex items-center gap-3 text-xs">
            <span className="text-slate-600 w-20 shrink-0 tabular-nums">
              {new Date(e.timestamp).toLocaleTimeString([], { hour12: false })}
            </span>
            <span className="w-24 shrink-0 text-slate-500">{e.actor}</span>
            <span className="text-slate-200">{LABELS[e.event_type] || e.event_type}</span>
>>>>>>> ff3b8e6d1f4bd3c8d0eb54f5fb1847df4306cdb3
            {e.details?.instruction && (
              <span className="text-cyan-400/80 italic">&ldquo;{e.details.instruction}&rdquo;</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

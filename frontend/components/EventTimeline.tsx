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

// Backend REST timestamps can be naive UTC (no "Z"); treat them as UTC, not local time.
const parseTs = (ts: string) => new Date(/([zZ]|[+-]\d{2}:?\d{2})$/.test(ts) ? ts : `${ts}Z`);

const dotColor = (t: string) =>
  /failed|rejected|cancelled/.test(t) ? "#a84d3e"
  : /completed|granted/.test(t) ? "#2c5a4a"
  : /approval|paused|redirect/.test(t) ? "#c79e4e"
  : "#789184";
export default function EventTimeline({ events }: { events: EventItem[] }) {
  const ordered = [...events].reverse();
  return (
    <div className="h-full flex flex-col">
      <div className="panel-heading flex items-center gap-2">
        <Activity size={13} /> Live activity <span className="event-count">{events.length} events</span>
      </div>
      <div className="flex-1 overflow-y-auto px-4 py-2 space-y-1.5">
        {ordered.length === 0 && (
          <div className="text-xs text-slate-600">No events yet.</div>
        )}
        {ordered.map((e) => (
          <div key={e.id} className="event-row">
            <span className="text-slate-400 tabular-nums">
              {parseTs(e.timestamp).toLocaleTimeString([], { hour12: false })}
            </span>
            <span className="text-slate-400 break-words">{e.actor}</span>
            <span className="event-description text-slate-200"><i style={{ background: dotColor(e.event_type) }} />{LABELS[e.event_type] || e.event_type}</span>
            {e.details?.instruction && (
              <span className="text-cyan-400/80 italic">&ldquo;{e.details.instruction}&rdquo;</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

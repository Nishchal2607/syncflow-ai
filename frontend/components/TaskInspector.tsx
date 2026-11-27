"use client";
import { Task } from "@/types";
import { AlertTriangle, FileSearch, Info } from "lucide-react";

export default function TaskInspector({ task }: { task: Task | null }) {
  if (!task) {
    return (
      <div><div className="panel-heading">Agent inspector</div><div className="p-6 text-sm text-slate-400 flex items-center gap-2">
        <Info size={14} /> Select a task node to inspect its details.
      </div></div>
    );
  }

  const uncertaintyColor =
    task.uncertainty === "low" ? "text-emerald-400" :
    task.uncertainty === "medium" ? "text-amber-400" : "text-rose-400";

  return (
    <div className="inspector-content space-y-5 overflow-y-auto h-full text-sm">
      <div className="panel-heading">Agent inspector</div>
      <div className="agent-summary">
        <div className="text-[11px] uppercase tracking-wide text-slate-500">{task.agent} agent</div>
        <div className="text-base font-medium text-slate-100">{task.name}</div>
        <div className="text-xs text-slate-500 mt-0.5">Status · {task.status}</div>
      </div>

      {task.objective && (
        <div>
          <div className="text-[11px] uppercase tracking-wide text-slate-500 mb-1">Objective</div>
          <div className="text-slate-300 leading-relaxed">{task.objective}</div>
        </div>
      )}

      {task.intended_next_action && (
        <div>
          <div className="text-[11px] uppercase tracking-wide text-slate-500 mb-1">Intended next action</div>
          <div className="text-slate-300 leading-relaxed">{task.intended_next_action}</div>
        </div>
      )}

      {task.result && (
        <div>
          <div className="text-[11px] uppercase tracking-wide text-slate-500 mb-1">Result</div>
          <div className="text-slate-200 leading-relaxed break-words">{task.result}</div>
        </div>
      )}

      {task.explanation && (
        <div>
          <div className="text-[11px] uppercase tracking-wide text-slate-500 mb-1">Decision explanation</div>
          <div className="text-slate-300 leading-relaxed break-words">{task.explanation}</div>
        </div>
      )}

      {task.evidence && task.evidence.length > 0 && (
        <div>
          <div className="text-[11px] uppercase tracking-wide text-slate-500 mb-1 flex items-center gap-1">
            <FileSearch size={12} /> Evidence
          </div>
          <ul className="space-y-1">
            {task.evidence.map((e, i) => (
              <li key={i} className="text-slate-400 text-xs bg-bg-elevated rounded-md px-2 py-1 border border-border">
                {String(e)}
              </li>
            ))}
          </ul>
        </div>
      )}

      {task.uncertainty && (
        <div className="flex items-center gap-2">
          <span className="text-[11px] uppercase tracking-wide text-slate-500">Uncertainty</span>
          <span className={`text-xs font-medium ${uncertaintyColor}`}>{task.uncertainty}</span>
        </div>
      )}

      {task.limitations && (
        <div className="flex gap-2 items-start bg-amber-500/5 border border-amber-500/20 rounded-md p-2">
          <AlertTriangle size={14} className="text-amber-400 mt-0.5 shrink-0" />
          <div className="text-xs text-amber-200/90 leading-relaxed break-words">{task.limitations}</div>
        </div>
      )}
    </div>
  );
}

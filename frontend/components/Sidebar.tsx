"use client";
import { Sparkles, Plus, Circle, Activity, Workflow, FileText } from "lucide-react";

export default function Sidebar({
  onNewSession, sessionId,
}: { onNewSession: () => void; sessionId: string | null }) {
  return (
    <header className="topbar">
      <a className="brand" href="#workspace" aria-label="SyncFlow AI workspace">
        <span className="brand-mark"><Sparkles size={18} /></span>
        <span className="brand-copy">
          <strong>SYNCFLOW <i>AI</i></strong>
          <small>Human-agent interaction</small>
        </span>
      </a>

      <nav className="top-nav" aria-label="Workspace sections">
        <a href="#workspace" aria-current="page"><Workflow size={14} /> Workspace</a>
        {sessionId && <>
          <a href="#workflow"><Activity size={14} /> Live workflow</a>
          <a href="#activity"><Circle size={12} /> Activity log</a>
          <a href="#result"><FileText size={13} /> Result</a>
        </>}
      </nav>

      <div className="top-actions">
        <button onClick={onNewSession} className="new-session-button">
          <Plus size={15} /> New session
        </button>
      </div>
    </header>
  );
}

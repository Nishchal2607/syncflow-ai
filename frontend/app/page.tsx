"use client";
import { useEffect, useState } from "react";
import { api } from "@/services/api";
import { useSession } from "@/hooks/useSession";
import Sidebar from "@/components/Sidebar";
import GoalInput from "@/components/GoalInput";
import ControlBar from "@/components/ControlBar";
import WorkflowGraph from "@/components/WorkflowGraph";
import TaskInspector from "@/components/TaskInspector";
import ReportPanel from "@/components/ReportPanel";
import EventTimeline from "@/components/EventTimeline";
import ApprovalModal from "@/components/ApprovalModal";

export default function Home() {
  const [mode, setMode] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const { connected, session, events, pendingApproval, setPendingApproval, refresh } = useSession(sessionId);

  useEffect(() => {
    setSessionId(localStorage.getItem("syncflow.activeSession"));
  }, []);

  useEffect(() => {
    api.health().then((h) => setMode(h.mode)).catch(() => setMode("unavailable"));
  }, []);

  const handleNewGoal = async (goal: string) => {
    const s = await api.createSession(goal);
    setSelectedTaskId(null);
    localStorage.setItem("syncflow.activeSession", s.id);
    setSessionId(s.id); // subscribe first so no early events are missed
    await api.startSession(s.id);
  };

  const withBusy = async (fn: () => Promise<any>) => {
    setBusy(true);
    try {
      await fn();
    } catch (e) {
      console.error(e);
    } finally {
      setBusy(false);
    }
  };

  const selectedTask = session?.tasks.find((t) => t.id === selectedTaskId) || null;
  const reportTask = session?.tasks.find((task) => task.agent === "reporter") || null;

  return (
    <div className="app-shell" id="workspace">
      <Sidebar sessionId={sessionId} onNewSession={() => { localStorage.removeItem("syncflow.activeSession"); setSessionId(null); setSelectedTaskId(null); }} />

      <main className="workspace-main">
        <section className="hero-banner">
          <div className="hero-copy">
            <div className="hero-eyebrow">HUMAN-AGENT WORKSPACE</div>
            <h1>Change the direction.<br /><em>See what moves.</em></h1>
            <p>Follow each step, steer the work while it runs, and review the result before you approve it.</p>
          </div>
          {session && (
            <div className="hero-session">
              <span className={`connection-status ${connected ? "is-connected" : "is-disconnected"}`} role="status">
                <i />{connected ? "Live connection" : "Reconnecting · state may be stale"}
              </span>
              <span className="session-label">SESSION / {session.id.slice(0, 8).toUpperCase()}</span>
            </div>
          )}
        </section>

        {!sessionId || !session ? (
          <div className="new-goal-wrap"><GoalInput onSubmit={handleNewGoal} /></div>
        ) : (
          <>
          <section className="dashboard-grid">
            <aside className="requirements-rail" aria-label="Goal and workflow controls">
              <div className="rail-section">
                <div className="rail-kicker">YOUR REQUIREMENT</div>
                <h2>Active goal</h2>
                <p className="rail-goal">{session.goal}</p>
              </div>
              <ControlBar
                goal=""
                status={session.status}
                busy={busy || !connected}
                onPause={() => withBusy(() => api.pauseSession(sessionId))}
                onResume={() => withBusy(() => api.resumeSession(sessionId))}
                onRedirect={(instr) => withBusy(() => api.redirectSession(sessionId, instr))}
                onCancel={() => withBusy(() => api.cancelSession(sessionId))}
              />
              <div className="rail-note">
                <strong>Human control</strong>
                <span>Pause at a checkpoint, redirect pending work, then resume when you are ready.</span>
              </div>
            </aside>

            <section className="workflow-column" id="workflow" aria-label="Live workflow">
              <div className="workflow-summary">
                <div>
                  <span className="section-kicker">LIVE EXECUTION</span>
                  <h2>Agent workflow</h2>
                </div>
                <span className={`status-pill status-${session.status.toLowerCase()}`}>
                  <i />{session.status.replace(/_/g, " ")}
                </span>
              </div>
              <div className="metrics">
                {[
                  { label: "Tasks", value: session.tasks.length },
                  { label: "Completed", value: session.tasks.filter((t) => t.status === "completed").length },
                  { label: "In progress", value: session.tasks.filter((t) => t.status === "running").length },
                  { label: "Progress", value: `${session.tasks.length ? Math.round(session.tasks.filter((t) => t.status === "completed").length / session.tasks.length * 100) : 0}%` },
                ].map((metric) => (
                  <div className="metric" key={metric.label}>
                    <span>{metric.label}</span><strong>{metric.value}</strong>
                  </div>
                ))}
              </div>
              <div className="graph-panel paper-panel">
                <WorkflowGraph
                  tasks={session.tasks}
                  selectedId={selectedTaskId}
                  onSelect={setSelectedTaskId}
                />
              </div>
            </section>

            <aside className="proof-column" aria-label="Inspect and verify workflow">
              <div className="proof-panel paper-panel">
                <TaskInspector task={selectedTask} />
              </div>
              <div className="timeline-panel paper-panel" id="activity">
                <EventTimeline events={events} />
              </div>
            </aside>
          </section>
          <ReportPanel task={reportTask} sourceTasks={session.tasks} mode={mode} />
          </>
        )}
      </main>

      {pendingApproval && (
        <ApprovalModal
          approval={pendingApproval}
          busy={busy}
          onApprove={() =>
            withBusy(async () => {
              await api.approve(pendingApproval.id);
              setPendingApproval(null);
              await refresh();
            })
          }
          onReject={(feedback) =>
            withBusy(async () => {
              await api.reject(pendingApproval.id, feedback);
              setPendingApproval(null);
              await refresh();
            })
          }
        />
      )}
    </div>
  );
}

"use client";
import { useEffect, useState } from "react";
import { api } from "@/services/api";
import { useSession } from "@/hooks/useSession";
import Sidebar from "@/components/Sidebar";
import GoalInput from "@/components/GoalInput";
import ControlBar from "@/components/ControlBar";
import WorkflowGraph from "@/components/WorkflowGraph";
import TaskInspector from "@/components/TaskInspector";
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

  return (
    <div className="workspace">
      <Sidebar mode={mode} sessionId={sessionId} onNewSession={() => { localStorage.removeItem("syncflow.activeSession"); setSessionId(null); setSelectedTaskId(null); }} />

      <main className="workspace-main">
        {!sessionId || !session ? (
          <GoalInput onSubmit={handleNewGoal} />
        ) : (
          <>
            <header className="workspace-heading"><div><div className="eyebrow">WORKSPACE / ORCHESTRATION</div><h1>Execution overview</h1></div><span className="session-label">Session · {session.id.slice(0, 8)}</span></header>
            <div role="status">{connected ? "Live connection" : "Disconnected — reconnecting; displayed state may be stale"}</div>
            <ControlBar
              goal={session.goal}
              status={session.status}
              busy={busy || !connected}
              onPause={() => withBusy(() => api.pauseSession(sessionId))}
              onResume={() => withBusy(() => api.resumeSession(sessionId))}
              onRedirect={(instr) => withBusy(() => api.redirectSession(sessionId, instr))}
              onCancel={() => withBusy(() => api.cancelSession(sessionId))}
            />

            <div className="metrics">{[{label:"Total tasks",value:session.tasks.length},{label:"Completed",value:session.tasks.filter(t=>t.status === "completed").length},{label:"Running",value:session.tasks.filter(t=>t.status === "running").length},{label:"Progress",value:`${session.tasks.length ? Math.round(session.tasks.filter(t=>t.status === "completed").length / session.tasks.length * 100) : 0}%`}].map(m=><div className="metric" key={m.label}><span>{m.label}</span><strong>{m.value}</strong></div>)}</div>
            <div className="execution-grid">
              <div className="graph-panel panel">
                <WorkflowGraph
                  tasks={session.tasks}
                  selectedId={selectedTaskId}
                  onSelect={setSelectedTaskId}
                />
              </div>
              <div className="inspector-panel panel">
                <TaskInspector task={selectedTask} />
              </div>
            </div>

            <div className="timeline-panel panel">
              <EventTimeline events={events} />
            </div>
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

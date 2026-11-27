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
  const { session, events, pendingApproval, setPendingApproval, refresh } = useSession(sessionId);

  useEffect(() => {
    api.health().then((h) => setMode(h.mode)).catch(() => setMode("deterministic_fallback"));
  }, []);

  const handleNewGoal = async (goal: string) => {
    const s = await api.createSession(goal);
<<<<<<< HEAD
    setSelectedTaskId(null);
    setSessionId(s.id); // subscribe first so no early events are missed
    await api.startSession(s.id);
=======
    await api.startSession(s.id);
    setSessionId(s.id);
>>>>>>> ff3b8e6d1f4bd3c8d0eb54f5fb1847df4306cdb3
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
<<<<<<< HEAD
    <div className="workspace">
      <Sidebar mode={mode} sessionId={sessionId} onNewSession={() => { setSessionId(null); setSelectedTaskId(null); }} />

      <main className="workspace-main">
=======
    <div className="flex h-screen">
      <Sidebar mode={mode} sessionId={sessionId} onNewSession={() => setSessionId(null)} />

      <main className="flex-1 flex flex-col min-w-0">
>>>>>>> ff3b8e6d1f4bd3c8d0eb54f5fb1847df4306cdb3
        {!sessionId || !session ? (
          <GoalInput onSubmit={handleNewGoal} />
        ) : (
          <>
<<<<<<< HEAD
            <header className="workspace-heading"><div><div className="eyebrow">WORKSPACE / ORCHESTRATION</div><h1>Execution overview</h1></div><span className="session-label">Session · {session.id.slice(0, 8)}</span></header>
=======
>>>>>>> ff3b8e6d1f4bd3c8d0eb54f5fb1847df4306cdb3
            <ControlBar
              goal={session.goal}
              status={session.status}
              busy={busy}
              onPause={() => withBusy(() => api.pauseSession(sessionId))}
              onResume={() => withBusy(() => api.resumeSession(sessionId))}
              onRedirect={(instr) => withBusy(() => api.redirectSession(sessionId, instr))}
              onCancel={() => withBusy(() => api.cancelSession(sessionId))}
            />

<<<<<<< HEAD
            <div className="metrics">{[{label:"Total tasks",value:session.tasks.length},{label:"Completed",value:session.tasks.filter(t=>t.status === "completed").length},{label:"Running",value:session.tasks.filter(t=>t.status === "running").length},{label:"Progress",value:`${session.tasks.length ? Math.round(session.tasks.filter(t=>t.status === "completed").length / session.tasks.length * 100) : 0}%`}].map(m=><div className="metric" key={m.label}><span>{m.label}</span><strong>{m.value}</strong></div>)}</div>
            <div className="execution-grid">
              <div className="graph-panel panel">
=======
            <div className="flex-1 flex min-h-0">
              <div className="flex-1 min-w-0 border-r border-border">
>>>>>>> ff3b8e6d1f4bd3c8d0eb54f5fb1847df4306cdb3
                <WorkflowGraph
                  tasks={session.tasks}
                  selectedId={selectedTaskId}
                  onSelect={setSelectedTaskId}
                />
              </div>
<<<<<<< HEAD
              <div className="inspector-panel panel">
=======
              <div className="w-80 shrink-0 bg-bg-panel">
>>>>>>> ff3b8e6d1f4bd3c8d0eb54f5fb1847df4306cdb3
                <TaskInspector task={selectedTask} />
              </div>
            </div>

<<<<<<< HEAD
            <div className="timeline-panel panel">
=======
            <div className="h-48 border-t border-border bg-bg-panel">
>>>>>>> ff3b8e6d1f4bd3c8d0eb54f5fb1847df4306cdb3
              <EventTimeline events={events} />
            </div>
          </>
        )}
      </main>

      {pendingApproval && (
        <ApprovalModal
          approval={pendingApproval}
<<<<<<< HEAD
          busy={busy}
=======
>>>>>>> ff3b8e6d1f4bd3c8d0eb54f5fb1847df4306cdb3
          onApprove={() =>
            withBusy(async () => {
              await api.approve(pendingApproval.id);
              setPendingApproval(null);
              await refresh();
            })
          }
          onReject={() =>
            withBusy(async () => {
              await api.reject(pendingApproval.id);
              setPendingApproval(null);
              await refresh();
            })
          }
        />
      )}
    </div>
  );
}

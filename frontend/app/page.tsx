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
    await api.startSession(s.id);
    setSessionId(s.id);
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
    <div className="flex h-screen">
      <Sidebar mode={mode} sessionId={sessionId} onNewSession={() => setSessionId(null)} />

      <main className="flex-1 flex flex-col min-w-0">
        {!sessionId || !session ? (
          <GoalInput onSubmit={handleNewGoal} />
        ) : (
          <>
            <ControlBar
              goal={session.goal}
              status={session.status}
              busy={busy}
              onPause={() => withBusy(() => api.pauseSession(sessionId))}
              onResume={() => withBusy(() => api.resumeSession(sessionId))}
              onRedirect={(instr) => withBusy(() => api.redirectSession(sessionId, instr))}
              onCancel={() => withBusy(() => api.cancelSession(sessionId))}
            />

            <div className="flex-1 flex min-h-0">
              <div className="flex-1 min-w-0 border-r border-border">
                <WorkflowGraph
                  tasks={session.tasks}
                  selectedId={selectedTaskId}
                  onSelect={setSelectedTaskId}
                />
              </div>
              <div className="w-80 shrink-0 bg-bg-panel">
                <TaskInspector task={selectedTask} />
              </div>
            </div>

            <div className="h-48 border-t border-border bg-bg-panel">
              <EventTimeline events={events} />
            </div>
          </>
        )}
      </main>

      {pendingApproval && (
        <ApprovalModal
          approval={pendingApproval}
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

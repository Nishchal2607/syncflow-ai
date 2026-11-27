"use client";
import { useEffect, useRef, useState, useCallback } from "react";
import { SessionData, EventItem, Approval, Task } from "@/types";
import { api, WS_BASE } from "@/services/api";

export function useSession(sessionId: string | null) {
  const [session, setSession] = useState<SessionData | null>(null);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [pendingApproval, setPendingApproval] = useState<Approval | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const refresh = useCallback(async () => {
    if (!sessionId) return;
    const [s, e] = await Promise.all([api.getSession(sessionId), api.getEvents(sessionId)]);
    setSession(s);
    setEvents(e);
  }, [sessionId]);

  useEffect(() => {
    if (!sessionId) return;
    refresh();

    const ws = new WebSocket(`${WS_BASE}/ws/sessions/${sessionId}`);
    wsRef.current = ws;

    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.type === "session_status") {
        setSession((prev) => (prev ? { ...prev, status: msg.status } : prev));
      } else if (msg.type === "task_update") {
        const t: Task = msg.task;
        setSession((prev) => {
          if (!prev) return prev;
          const existing = prev.tasks.find((x) => x.id === t.id);
          const tasks = existing
            ? prev.tasks.map((x) => (x.id === t.id ? t : x))
            : [...prev.tasks, t];
          return { ...prev, tasks };
        });
      } else if (msg.type === "event") {
        setEvents((prev) => [...prev, msg.event]);
      } else if (msg.type === "approval_request") {
        setPendingApproval(msg.approval);
      } else if (msg.type === "approval_resolved") {
        setPendingApproval((prev) => (prev && prev.id === msg.approval_id ? null : prev));
      }
    };

    ws.onclose = () => {
      wsRef.current = null;
    };

    return () => {
      ws.close();
    };
  }, [sessionId, refresh]);

  return { session, events, pendingApproval, setPendingApproval, refresh };
}

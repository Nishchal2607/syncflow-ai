"use client";
import { useEffect, useRef, useState, useCallback } from "react";
import { SessionData, EventItem, Approval, Task } from "@/types";
import { api, WS_BASE } from "@/services/api";

const mergeEvents = (prev: EventItem[], incoming: EventItem[]) => {
  const seen = new Set(prev.map((e) => e.id));
  return [...prev, ...incoming.filter((e) => !seen.has(e.id))];
};

export function useSession(sessionId: string | null) {
  const [session, setSession] = useState<SessionData | null>(null);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [pendingApproval, setPendingApproval] = useState<Approval | null>(null);
  const activeId = useRef<string | null>(null);

  const refresh = useCallback(async () => {
    if (!sessionId) return;
    try {
      const [s, e] = await Promise.all([api.getSession(sessionId), api.getEvents(sessionId)]);
      if (activeId.current !== sessionId) return; // stale response from a previous session
      setSession(s);
      setEvents((prev) => mergeEvents(e, prev));
    } catch (err) {
      console.error("refresh failed", err);
    }
  }, [sessionId]);

  useEffect(() => {
    activeId.current = sessionId;
    // Clear state from the previous session so it never flashes under the new id
    setSession(null);
    setEvents([]);
    setPendingApproval(null);
    if (!sessionId) return;

    let ws: WebSocket | null = null;
    let retry: ReturnType<typeof setTimeout> | null = null;
    let closed = false;

    const connect = () => {
      ws = new WebSocket(`${WS_BASE}/ws/sessions/${sessionId}`);
      ws.onopen = () => { refresh(); }; // close any gap after (re)connect
      ws.onmessage = (ev) => {
        let msg: any;
        try { msg = JSON.parse(ev.data); } catch { return; }
        if (msg.type === "session_status") {
          setSession((prev) => (prev ? { ...prev, status: msg.status } : prev));
        } else if (msg.type === "task_update") {
          const t: Task = msg.task;
          setSession((prev) => {
            if (!prev) return prev;
            const exists = prev.tasks.some((x) => x.id === t.id);
            const tasks = exists ? prev.tasks.map((x) => (x.id === t.id ? t : x)) : [...prev.tasks, t];
            return { ...prev, tasks };
          });
        } else if (msg.type === "event") {
          setEvents((prev) => mergeEvents(prev, [msg.event]));
        } else if (msg.type === "approval_request") {
          setPendingApproval(msg.approval);
        } else if (msg.type === "approval_resolved") {
          setPendingApproval((prev) => (prev && prev.id === msg.approval_id ? null : prev));
        }
      };
      ws.onclose = () => {
        if (!closed) retry = setTimeout(connect, 1500);
      };
    };
    connect();
    refresh();

    return () => {
      closed = true;
      if (retry) clearTimeout(retry);
      ws?.close();
    };
  }, [sessionId, refresh]);

  return { session, events, pendingApproval, setPendingApproval, refresh };
}

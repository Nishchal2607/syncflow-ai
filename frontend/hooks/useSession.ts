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
  const [connected, setConnected] = useState(false);
  const generation = useRef(0);
  const activeId = useRef<string | null>(null);

  const refresh = useCallback(async () => {
    if (!sessionId) return;
    try {
      const request = ++generation.current;
      const [s, e, approvals] = await Promise.all([api.getSession(sessionId), api.getEvents(sessionId), api.getApprovals(sessionId)]);
      if (activeId.current !== sessionId || request !== generation.current) return; // stale response from a previous session
      setSession(s);
      setPendingApproval(approvals[0] ?? null);
      setEvents((prev) => mergeEvents(e, prev));
    } catch (err) {
      console.error("refresh failed", err);
    }
  }, [sessionId]);

  useEffect(() => {
    activeId.current = sessionId;
    setConnected(false);
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
      ws.onopen = () => { if (!closed) { setConnected(true); refresh(); } }; // close any gap after (re)connect
      ws.onmessage = (ev) => {
        if (closed) return;
        generation.current++;
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
        if (!closed) { setConnected(false); retry = setTimeout(connect, 1500); }
      };
    };
    connect();
    refresh();
    const poll = setInterval(refresh, 3000);

    return () => {
      closed = true;
      generation.current++;
      clearInterval(poll);
      if (retry) clearTimeout(retry);
      ws?.close();
    };
  }, [sessionId, refresh]);

  return { connected, session, events, pendingApproval, setPendingApproval, refresh };
}

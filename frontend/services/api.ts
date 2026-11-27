import { SessionData, EventItem, Approval } from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

async function req<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status}: ${body}`);
  }
  return res.json();
}

export const api = {
  health: () => req<{ status: string; mode: string }>("/api/health"),
  createSession: (goal: string) =>
    req<SessionData>("/api/sessions", { method: "POST", body: JSON.stringify({ goal }) }),
  getSession: (id: string) => req<SessionData>(`/api/sessions/${id}`),
  startSession: (id: string) => req<SessionData>(`/api/sessions/${id}/start`, { method: "POST" }),
  pauseSession: (id: string) => req<SessionData>(`/api/sessions/${id}/pause`, { method: "POST" }),
  resumeSession: (id: string) => req<SessionData>(`/api/sessions/${id}/resume`, { method: "POST" }),
  cancelSession: (id: string) => req<SessionData>(`/api/sessions/${id}/cancel`, { method: "POST" }),
  redirectSession: (id: string, instruction: string, task_id?: string) =>
    req<SessionData>(`/api/sessions/${id}/redirect`, {
      method: "POST",
      body: JSON.stringify({ instruction, task_id }),
    }),
  getApprovals: (id: string) => req<Approval[]>(`/api/sessions/${id}/approvals`),
  getEvents: (id: string) => req<EventItem[]>(`/api/sessions/${id}/events`),
  approve: (approvalId: string) =>
    req(`/api/approvals/${approvalId}/approve`, { method: "POST" }),
  reject: (approvalId: string) =>
    req(`/api/approvals/${approvalId}/reject`, { method: "POST" }),
};

export const WS_BASE = (process.env.NEXT_PUBLIC_WS_BASE || "ws://localhost:8000");

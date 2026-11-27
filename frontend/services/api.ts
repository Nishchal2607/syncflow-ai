import { SessionData, EventItem, Approval, Intervention } from "@/types";

const commandId = () =>
  typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `cmd_${Date.now()}_${Math.random().toString(36).slice(2)}`;

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
  pauseSession: (id: string) => req<SessionData>(`/api/sessions/${id}/pause`, { method: "POST", body: JSON.stringify({ command_id: commandId() }) }),
  resumeSession: (id: string) => req<SessionData>(`/api/sessions/${id}/resume`, { method: "POST", body: JSON.stringify({ command_id: commandId() }) }),
  cancelSession: (id: string) => req<SessionData>(`/api/sessions/${id}/cancel`, { method: "POST", body: JSON.stringify({ command_id: commandId() }) }),
  redirectSession: (id: string, instruction: string, task_id?: string) =>
    req<SessionData>(`/api/sessions/${id}/redirect`, {
      method: "POST",
      body: JSON.stringify({ instruction, task_id, command_id: commandId() }),
    }),
  getApprovals: (id: string) => req<Approval[]>(`/api/sessions/${id}/approvals`),
  getEvents: (id: string) => req<EventItem[]>(`/api/sessions/${id}/events`),
  approve: (approvalId: string) =>
    req(`/api/approvals/${approvalId}/approve`, { method: "POST", body: JSON.stringify({ command_id: commandId() }) }),
  reject: (approvalId: string, feedback?: string) =>
    req(`/api/approvals/${approvalId}/reject`, { method: "POST", body: JSON.stringify({ command_id: commandId(), feedback }) }),
  editTask: (sessionId: string, taskId: string, body: Record<string, any>) =>
    req<SessionData>(`/api/sessions/${sessionId}/tasks/${taskId}`, {
      method: "PATCH",
      body: JSON.stringify({ ...body, command_id: commandId() }),
    }),
  addTask: (sessionId: string, body: Record<string, any>) =>
    req<SessionData>(`/api/sessions/${sessionId}/tasks`, {
      method: "POST",
      body: JSON.stringify({ ...body, command_id: commandId() }),
    }),
  removeTask: (sessionId: string, taskId: string, reason?: string) =>
    req<SessionData>(`/api/sessions/${sessionId}/tasks/${taskId}`, {
      method: "DELETE",
      body: JSON.stringify({ reason, command_id: commandId() }),
    }),
  reprioritize: (sessionId: string, taskIds: string[], reason?: string) =>
    req<SessionData>(`/api/sessions/${sessionId}/reprioritize`, {
      method: "POST",
      body: JSON.stringify({ task_ids: taskIds, reason, command_id: commandId() }),
    }),
  getInterventions: (sessionId: string) =>
    req<Intervention[]>(`/api/sessions/${sessionId}/interventions`),
};

export const WS_BASE = (process.env.NEXT_PUBLIC_WS_BASE || "ws://localhost:8000");

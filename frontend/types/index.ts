export type SessionStatus =
  | "IDLE" | "PLANNING" | "RUNNING" | "PAUSED"
  | "AWAITING_APPROVAL" | "COMPLETED" | "FAILED" | "CANCELLED";

export type TaskStatus = "pending" | "running" | "completed" | "failed" | "paused" | "skipped";

export type AgentRole = "planner" | "research" | "verification" | "reporter";

export interface Task {
  id: string;
  name: string;
  agent: AgentRole;
  status: TaskStatus;
  order_index: number;
  depends_on: string[];
  result?: string | null;
  explanation?: string | null;
  evidence?: any[] | null;
  uncertainty?: string | null;
  limitations?: string | null;
  retry_count?: number;
  max_retries?: number;
  timeout_seconds?: number;
  checkpoint?: Record<string, any> | null;
  objective?: string | null;
  intended_next_action?: string | null;
  capabilities?: string[] | null;
  human_assistance_conditions?: string[] | null;
}

export interface SessionData {
  id: string;
  goal: string;
  status: SessionStatus;
  current_task_id: string | null;
  created_at: string;
  updated_at: string;
  tasks: Task[];
}

export interface EventItem {
  id: string;
  session_id: string;
  event_type: string;
  actor: string;
  task_id: string | null;
  details: Record<string, any> | null;
  timestamp: string;
  sequence?: number;
}

export interface Approval {
  id: string;
  session_id: string;
  task_id: string | null;
  proposed_action: string;
  expected_impact: string;
  evidence?: any[] | null;
  status: "pending" | "approved" | "rejected";
  created_at: string;
  resolved_at?: string | null;
  feedback?: string | null;
}

export interface Intervention {
  id: string;
  session_id: string;
  task_id: string | null;
  action: string;
  actor: string;
  reason: string | null;
  before: Record<string, any> | null;
  after: Record<string, any> | null;
  created_at: string;
}

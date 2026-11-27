from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field


# ---------- Session ----------

class SessionCreateRequest(BaseModel):
    goal: str = Field(..., min_length=3, max_length=2000)


class TaskOut(BaseModel):
    id: str
    name: str
    agent: str
    status: str
    order_index: int
    depends_on: list[str]
    result: Optional[str] = None
    explanation: Optional[str] = None
    evidence: Optional[list[Any]] = None
    uncertainty: Optional[str] = None
    limitations: Optional[str] = None

    class Config:
        from_attributes = True


class SessionOut(BaseModel):
    id: str
    goal: str
    status: str
    current_task_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    tasks: list[TaskOut] = []

    class Config:
        from_attributes = True


class RedirectRequest(BaseModel):
    task_id: Optional[str] = Field(
        None, description="Target task to redirect. Defaults to current running/next task."
    )
    instruction: str = Field(..., min_length=3, max_length=2000)


class ApprovalOut(BaseModel):
    id: str
    session_id: str
    task_id: Optional[str]
    proposed_action: str
    expected_impact: str
    evidence: Optional[list[Any]] = None
    status: str
    created_at: datetime
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class EventOut(BaseModel):
    id: str
    session_id: str
    event_type: str
    actor: str
    task_id: Optional[str] = None
    details: Optional[dict] = None
    timestamp: datetime

    class Config:
        from_attributes = True


class HealthOut(BaseModel):
    status: str
    mode: str  # "llm" | "deterministic_fallback"

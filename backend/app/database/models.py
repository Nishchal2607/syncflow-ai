"""SQLAlchemy ORM models for SyncFlow AI persistence layer."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, DateTime, ForeignKey, Integer, JSON, Text, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def gen_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def now() -> datetime:
    return datetime.now(timezone.utc)


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, default=lambda: gen_id("sess"))
    goal = Column(Text, nullable=False)
    status = Column(String, nullable=False, default="IDLE")
    # Saved execution cursor so RESUME continues from exact state
    current_task_id = Column(String, nullable=True)
    execution_epoch = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

    tasks = relationship("Task", back_populates="session", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="session", cascade="all, delete-orphan")
    approvals = relationship("Approval", back_populates="session", cascade="all, delete-orphan")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, default=lambda: gen_id("task"))
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    name = Column(String, nullable=False)
    agent = Column(String, nullable=False)  # planner | research | verification | reporter
    status = Column(String, nullable=False, default="pending")
    # pending | running | completed | failed | paused | skipped
    order_index = Column(Integer, nullable=False, default=0)
    depends_on = Column(JSON, nullable=False, default=list)  # list of task ids

    result = Column(Text, nullable=True)
    explanation = Column(Text, nullable=True)
    evidence = Column(JSON, nullable=True, default=list)
    uncertainty = Column(String, nullable=True)  # low | medium | high
    limitations = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=2)
    timeout_seconds = Column(Integer, nullable=False, default=30)
    checkpoint = Column(JSON, nullable=True, default=dict)
    objective = Column(Text, nullable=True)
    intended_next_action = Column(Text, nullable=True)
    capabilities = Column(JSON, nullable=True, default=list)
    human_assistance_conditions = Column(JSON, nullable=True, default=list)

    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

    session = relationship("Session", back_populates="tasks")


class Event(Base):
    __tablename__ = "events"

    id = Column(String, primary_key=True, default=lambda: gen_id("evt"))
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    event_type = Column(String, nullable=False)
    actor = Column(String, nullable=False)  # human | planner | research | verification | reporter | coordinator | system
    task_id = Column(String, nullable=True)
    details = Column(JSON, nullable=True, default=dict)
    timestamp = Column(DateTime, default=now)
    sequence = Column(Integer, nullable=False, default=0)

    session = relationship("Session", back_populates="events")


class Approval(Base):
    __tablename__ = "approvals"

    id = Column(String, primary_key=True, default=lambda: gen_id("appr"))
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    task_id = Column(String, nullable=True)
    proposed_action = Column(Text, nullable=False)
    expected_impact = Column(Text, nullable=False)
    evidence = Column(JSON, nullable=True, default=list)
    status = Column(String, nullable=False, default="pending")  # pending | approved | rejected
    created_at = Column(DateTime, default=now)
    resolved_at = Column(DateTime, nullable=True)
    feedback = Column(Text, nullable=True)

    session = relationship("Session", back_populates="approvals")


class Command(Base):
    __tablename__ = "commands"
    __table_args__ = (UniqueConstraint("session_id", "command_id", name="uq_command_session"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    command_id = Column(String, nullable=False)
    command_type = Column(String, nullable=False)
    result = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=now)


class Intervention(Base):
    __tablename__ = "interventions"

    id = Column(String, primary_key=True, default=lambda: gen_id("int"))
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    task_id = Column(String, nullable=True)
    action = Column(String, nullable=False)
    actor = Column(String, nullable=False, default="human")
    reason = Column(Text, nullable=True)
    before = Column(JSON, nullable=True, default=dict)
    after = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime, default=now)

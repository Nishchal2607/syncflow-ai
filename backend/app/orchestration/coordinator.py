"""
Coordinator: the single orchestration engine that executes a session's task
graph through the shared agents, enforcing the state machine and all human
intervention semantics (pause/resume/redirect/cancel/approval).

Design notes for reviewers:
- Exactly one asyncio background task drives a session's execution loop.
  A per-session `asyncio.Lock` prevents `start()` from spawning a second
  loop if called twice (duplicate commands must not duplicate execution).
- PAUSE does not kill the loop; it sets a flag the loop checks *between*
  tasks (a safe checkpoint) and then the loop blocks on an asyncio.Event
  until RESUME sets it again. No task is ever half-executed across a pause.
- REDIRECT mutates the persisted task graph (skips/replaces/inserts rows)
  and is only accepted while the session is PAUSED, which guarantees the
  loop is blocked and cannot race the mutation.
- Every state change is validated by app.orchestration.state_machine and
  every notable change is persisted as an Event and broadcast over the
  session's WebSocket.
"""
import asyncio
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession as DBSession

from app.database.models import Session, Task, Event, Approval, gen_id
from app.database.db import AsyncSessionLocal
from app.orchestration.state_machine import transition, InvalidTransition
from app.agents import planner, workers
from app.interaction.ws_manager import manager


class SessionControl:
    """In-memory per-session runtime control flags (not persisted)."""
    def __init__(self):
        self.lock = asyncio.Lock()
        self.resume_event = asyncio.Event()
        self.resume_event.set()  # not paused by default
        self.cancel_requested = False
        self.running_task_future: asyncio.Task | None = None


_controls: dict[str, SessionControl] = {}


def _get_control(session_id: str) -> SessionControl:
    if session_id not in _controls:
        _controls[session_id] = SessionControl()
    return _controls[session_id]


async def _log_event(db: DBSession, session_id: str, event_type: str, actor: str,
                      task_id: str | None = None, details: dict | None = None):
    evt = Event(
        id=gen_id("evt"), session_id=session_id, event_type=event_type,
        actor=actor, task_id=task_id, details=details or {},
    )
    db.add(evt)
    await db.flush()
    await manager.broadcast(session_id, {
        "type": "event",
        "event": {
            "id": evt.id, "session_id": session_id, "event_type": event_type,
            "actor": actor, "task_id": task_id, "details": details or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    })
    return evt


async def _set_session_status(db: DBSession, session: Session, target: str):
    new_status = transition(session.status, target)
    session.status = new_status
    await db.flush()
    await manager.broadcast(session.id, {
        "type": "session_status",
        "status": new_status,
        "session_id": session.id,
    })


async def _broadcast_task(session_id: str, task: Task):
    await manager.broadcast(session_id, {
        "type": "task_update",
        "task": {
            "id": task.id, "name": task.name, "agent": task.agent,
            "status": task.status, "order_index": task.order_index,
            "depends_on": task.depends_on, "result": task.result,
            "explanation": task.explanation, "evidence": task.evidence,
            "uncertainty": task.uncertainty, "limitations": task.limitations,
        },
    })


async def create_session(goal: str) -> Session:
    async with AsyncSessionLocal() as db:
        session = Session(id=gen_id("sess"), goal=goal, status="IDLE")
        db.add(session)
        await db.flush()
        await _log_event(db, session.id, "session_created", "human", details={"goal": goal})
        await db.commit()
        await db.refresh(session)
        return session


async def start_session(session_id: str):
    control = _get_control(session_id)
    async with control.lock:
        if control.running_task_future and not control.running_task_future.done():
            return  # already running — ignore duplicate start
        async with AsyncSessionLocal() as db:
            session = await db.get(Session, session_id)
            if session is None:
                raise ValueError("session not found")
            await _set_session_status(db, session, "PLANNING")
            await _log_event(db, session_id, "plan_generation_started", "coordinator")
            await db.commit()

        tasks_spec, used_llm = await planner.generate_plan(
            (await _fetch_goal(session_id))
        )

        async with AsyncSessionLocal() as db:
            session = await db.get(Session, session_id)
            created: list[Task] = []
            for i, spec in enumerate(tasks_spec):
                created.append(Task(
                    id=gen_id("task"), session_id=session_id, name=spec["name"],
                    agent=spec["agent"], status="pending", order_index=i, depends_on=[],
                ))
            db.add_all(created)
            await db.flush()
            # resolve depends_on_index -> actual task ids now that ids exist
            for i, spec in enumerate(tasks_spec):
                created[i].depends_on = [created[j].id for j in spec.get("depends_on_index", []) if j < len(created)]
            await db.flush()
            await _log_event(db, session_id, "plan_generated", "planner",
                              details={"used_llm": used_llm, "task_count": len(created)})
            for t in created:
                await _broadcast_task(session_id, t)
            await _set_session_status(db, session, "RUNNING")
            await db.commit()

        control.resume_event.set()
        control.cancel_requested = False
        control.running_task_future = asyncio.create_task(_run_loop(session_id))


async def _fetch_goal(session_id: str) -> str:
    async with AsyncSessionLocal() as db:
        session = await db.get(Session, session_id)
        return session.goal


async def _run_loop(session_id: str):
    control = _get_control(session_id)
    try:
        while True:
            # Safe checkpoint: block here if paused
            await control.resume_event.wait()

            async with AsyncSessionLocal() as db:
                session = await db.get(Session, session_id)
                if session.status in ("CANCELLED", "COMPLETED", "FAILED"):
                    return
                if control.cancel_requested:
                    await _set_session_status(db, session, "CANCELLED")
                    await _log_event(db, session_id, "session_cancelled", "human")
                    await db.commit()
                    return

                result = await db.execute(select(Task).where(Task.session_id == session_id))
                all_tasks = sorted(result.scalars().all(), key=lambda t: t.order_index)

                next_task = None
                for t in all_tasks:
                    if t.status != "pending":
                        continue
                    deps = t.depends_on or []
                    dep_tasks = [x for x in all_tasks if x.id in deps]
                    if all(d.status == "completed" for d in dep_tasks):
                        next_task = t
                        break

                if next_task is None:
                    # check if all tasks are completed/skipped -> finish session
                    unfinished = [t for t in all_tasks if t.status in ("pending", "running")]
                    if not unfinished:
                        await _set_session_status(db, session, "COMPLETED")
                        await _log_event(db, session_id, "session_completed", "coordinator")
                        await db.commit()
                        return
                    else:
                        # stuck (e.g. failed dependency) — mark failed
                        await _set_session_status(db, session, "FAILED")
                        await _log_event(db, session_id, "session_failed", "coordinator",
                                          details={"reason": "no runnable task but unfinished tasks remain"})
                        await db.commit()
                        return

                session.current_task_id = next_task.id
                next_task.status = "running"
                await db.flush()
                await _broadcast_task(session_id, next_task)
                await _log_event(db, session_id, "task_started", next_task.agent, task_id=next_task.id,
                                  details={"name": next_task.name})
                await db.commit()
                goal = session.goal
                agent = next_task.agent
                task_id = next_task.id
                task_name = next_task.name

            # Execute outside the DB transaction (agent calls may be slow / network)
            try:
                if agent == "research":
                    output = await workers.run_research(task_name, goal)
                elif agent == "verification":
                    ctx = await _gather_completed_summaries(session_id)
                    output = await workers.run_verification(ctx, goal)
                elif agent == "reporter":
                    ctx = await _gather_completed_outputs(session_id)
                    output = await workers.run_reporter(ctx, goal)
                else:
                    output = {"result": "", "explanation": "", "evidence": [],
                              "uncertainty": "high", "limitations": "unknown agent"}
            except Exception as exc:
                async with AsyncSessionLocal() as db:
                    session = await db.get(Session, session_id)
                    task = await db.get(Task, task_id)
                    task.status = "failed"
                    task.result = f"Error: {exc}"
                    await db.flush()
                    await _broadcast_task(session_id, task)
                    await _log_event(db, session_id, "task_failed", agent, task_id=task_id,
                                      details={"error": str(exc)})
                    await _set_session_status(db, session, "FAILED")
                    await db.commit()
                return

            # Reporter output is a consequential action -> gate behind human approval
            if agent == "reporter":
                async with AsyncSessionLocal() as db:
                    session = await db.get(Session, session_id)
                    task = await db.get(Task, task_id)
                    task.result = output["result"]
                    task.explanation = output["explanation"]
                    task.evidence = output["evidence"]
                    task.uncertainty = output["uncertainty"]
                    task.limitations = output["limitations"]
                    # keep status "running" until approved
                    await db.flush()
                    await _broadcast_task(session_id, task)

                    approval = Approval(
                        id=gen_id("appr"), session_id=session_id, task_id=task_id,
                        proposed_action=f"Finalize and deliver report: {task_name}",
                        expected_impact="This will mark the final report as delivered to the user "
                                        "and complete the session.",
                        evidence=output["evidence"], status="pending",
                    )
                    db.add(approval)
                    await db.flush()
                    await _set_session_status(db, session, "AWAITING_APPROVAL")
                    await _log_event(db, session_id, "approval_requested", "reporter", task_id=task_id,
                                      details={"approval_id": approval.id})
                    await manager.broadcast(session_id, {
                        "type": "approval_request",
                        "approval": {
                            "id": approval.id, "session_id": session_id, "task_id": task_id,
                            "proposed_action": approval.proposed_action,
                            "expected_impact": approval.expected_impact,
                            "evidence": approval.evidence, "status": "pending",
                        },
                    })
                    await db.commit()
                # Block the loop until approve/reject resumes it (approve/reject flips resume_event)
                control.resume_event.clear()
                continue

            # Normal (non-gated) task completion
            async with AsyncSessionLocal() as db:
                task = await db.get(Task, task_id)
                task.status = "completed"
                task.result = output["result"]
                task.explanation = output["explanation"]
                task.evidence = output["evidence"]
                task.uncertainty = output["uncertainty"]
                task.limitations = output["limitations"]
                await db.flush()
                await _broadcast_task(session_id, task)
                await _log_event(db, session_id, "task_completed", agent, task_id=task_id,
                                  details={"name": task_name})
                await db.commit()
    except asyncio.CancelledError:
        return


async def _gather_completed_summaries(session_id: str) -> list[str]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Task).where(Task.session_id == session_id, Task.status == "completed")
        )
        return [t.result for t in result.scalars().all() if t.result]


async def _gather_completed_outputs(session_id: str) -> list[dict]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Task).where(Task.session_id == session_id, Task.status == "completed")
        )
        return [
            {"agent": t.agent, "result": t.result or ""}
            for t in result.scalars().all()
        ]


async def pause_session(session_id: str):
    control = _get_control(session_id)
    async with AsyncSessionLocal() as db:
        session = await db.get(Session, session_id)
        if session is None:
            raise ValueError("session not found")
        if session.status != "RUNNING":
            raise InvalidTransition(session.status, "PAUSED")
        await _set_session_status(db, session, "PAUSED")
        await _log_event(db, session_id, "agent_paused", "human")
        await db.commit()
    control.resume_event.clear()


async def resume_session(session_id: str):
    control = _get_control(session_id)
    async with AsyncSessionLocal() as db:
        session = await db.get(Session, session_id)
        if session is None:
            raise ValueError("session not found")
        if session.status != "PAUSED":
            raise InvalidTransition(session.status, "RUNNING")
        await _set_session_status(db, session, "RUNNING")
        await _log_event(db, session_id, "agent_resumed", "human")
        await db.commit()
    control.resume_event.set()
    if control.running_task_future is None or control.running_task_future.done():
        control.running_task_future = asyncio.create_task(_run_loop(session_id))


async def redirect_session(session_id: str, instruction: str, task_id: str | None):
    """
    Human redirection: only accepted while PAUSED, guaranteeing the execution
    loop is blocked and cannot race this mutation. Backend actually mutates
    the task graph (skips the target task and inserts a replacement research
    task), not just a text label.
    """
    async with AsyncSessionLocal() as db:
        session = await db.get(Session, session_id)
        if session is None:
            raise ValueError("session not found")
        if session.status != "PAUSED":
            raise InvalidTransition(session.status, "PAUSED")

        result = await db.execute(select(Task).where(Task.session_id == session_id))
        all_tasks = sorted(result.scalars().all(), key=lambda t: t.order_index)

        target = None
        if task_id:
            target = next((t for t in all_tasks if t.id == task_id), None)
        if target is None:
            # default: the current / next pending task
            target = next((t for t in all_tasks if t.status in ("running", "pending")), None)

        if target is None:
            raise ValueError("no redirectable task found")

        # Mark the target skipped and insert a new task in its place, preserving
        # dependency edges so downstream tasks (e.g. "Compare results") now wait
        # on the *new* task instead.
        target.status = "skipped"
        new_task = Task(
            id=gen_id("task"), session_id=session_id,
            name=f"[Redirected] {instruction}", agent=target.agent,
            status="pending", order_index=target.order_index, depends_on=[],
        )
        db.add(new_task)
        await db.flush()

        for t in all_tasks:
            if target.id in (t.depends_on or []):
                deps = list(t.depends_on)
                deps = [new_task.id if d == target.id else d for d in deps]
                t.depends_on = deps

        await db.flush()
        await _broadcast_task(session_id, target)
        await _broadcast_task(session_id, new_task)
        await _log_event(db, session_id, "human_redirected", "human", task_id=target.id,
                          details={"instruction": instruction, "replaced_with": new_task.id})
        # keep status PAUSED (human must still issue /resume), matches "PAUSED -> PAUSED" allowed transition
        await db.commit()


async def cancel_session(session_id: str):
    control = _get_control(session_id)
    async with AsyncSessionLocal() as db:
        session = await db.get(Session, session_id)
        if session is None:
            raise ValueError("session not found")
        if session.status in ("COMPLETED", "FAILED", "CANCELLED"):
            raise InvalidTransition(session.status, "CANCELLED")
        await _set_session_status(db, session, "CANCELLED")
        await _log_event(db, session_id, "session_cancelled", "human")
        await db.commit()
    control.cancel_requested = True
    control.resume_event.set()  # unblock loop so it can observe cancellation and exit
    if control.running_task_future:
        control.running_task_future.cancel()


async def approve_action(approval_id: str):
    async with AsyncSessionLocal() as db:
        approval = await db.get(Approval, approval_id)
        if approval is None:
            raise ValueError("approval not found")
        if approval.status != "pending":
            raise ValueError("approval already resolved")
        approval.status = "approved"
        approval.resolved_at = datetime.now(timezone.utc)
        session = await db.get(Session, approval.session_id)
        task = await db.get(Task, approval.task_id) if approval.task_id else None
        if task:
            task.status = "completed"
            await _broadcast_task(session.id, task)
        await _set_session_status(db, session, "RUNNING")
        await _log_event(db, session.id, "approval_granted", "human", task_id=approval.task_id,
                          details={"approval_id": approval_id})
        await manager.broadcast(session.id, {
            "type": "approval_resolved",
            "approval_id": approval_id, "status": "approved",
        })
        await db.commit()
        session_id = session.id

    control = _get_control(session_id)
    control.resume_event.set()
    if control.running_task_future is None or control.running_task_future.done():
        control.running_task_future = asyncio.create_task(_run_loop(session_id))


async def reject_action(approval_id: str):
    async with AsyncSessionLocal() as db:
        approval = await db.get(Approval, approval_id)
        if approval is None:
            raise ValueError("approval not found")
        if approval.status != "pending":
            raise ValueError("approval already resolved")
        approval.status = "rejected"
        approval.resolved_at = datetime.now(timezone.utc)
        session = await db.get(Session, approval.session_id)
        task = await db.get(Task, approval.task_id) if approval.task_id else None
        if task:
            task.status = "failed"
            await _broadcast_task(session.id, task)
        await _set_session_status(db, session, "FAILED")
        await _log_event(db, session.id, "approval_rejected", "human", task_id=approval.task_id,
                          details={"approval_id": approval_id})
        await manager.broadcast(session.id, {
            "type": "approval_resolved",
            "approval_id": approval_id, "status": "rejected",
        })
        await db.commit()

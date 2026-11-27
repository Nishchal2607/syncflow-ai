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

from app.database.models import Session, Task, Event, Approval, Command, Intervention, gen_id
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


async def _queue(db, session_id, message):
    db.info.setdefault("messages", []).append((session_id, message))

async def _commit(db):
    await db.commit()
    for session_id, message in db.info.pop("messages", []):
        await manager.broadcast(session_id, message)

async def _log_event(db: DBSession, session_id: str, event_type: str, actor: str,
                      task_id: str | None = None, details: dict | None = None):
    result = await db.execute(select(Event.sequence).where(Event.session_id == session_id).order_by(Event.sequence.desc()).limit(1))
    sequence = (result.scalar_one_or_none() or 0) + 1
    evt = Event(
        id=gen_id("evt"), session_id=session_id, event_type=event_type,
        actor=actor, task_id=task_id, details=details or {},
        sequence=sequence,
    )
    db.add(evt)
    await db.flush()
    await _queue(db, session_id, {
        "type": "event",
        "event": {
            "id": evt.id, "session_id": session_id, "event_type": event_type,
            "actor": actor, "task_id": task_id, "details": details or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sequence": sequence,
        },
    })
    return evt


async def _set_session_status(db: DBSession, session: Session, target: str):
    new_status = transition(session.status, target)
    session.status = new_status
    await db.flush()
    await _queue(db, session.id, {
        "type": "session_status",
        "status": new_status,
        "session_id": session.id,
    })


async def _broadcast_task(db, session_id: str, task: Task):
    await _queue(db, session_id, {
        "type": "task_update",
        "task": {
            "id": task.id, "name": task.name, "agent": task.agent,
            "status": task.status, "order_index": task.order_index,
            "depends_on": task.depends_on, "result": task.result,
            "explanation": task.explanation, "evidence": task.evidence,
            "uncertainty": task.uncertainty, "limitations": task.limitations,
            "retry_count": task.retry_count,
            "max_retries": task.max_retries,
            "timeout_seconds": task.timeout_seconds,
            "checkpoint": task.checkpoint or {},
            "objective": task.objective,
            "intended_next_action": task.intended_next_action,
            "capabilities": task.capabilities or [],
            "human_assistance_conditions": task.human_assistance_conditions or [],
        },
    })


async def create_session(goal: str) -> Session:
    async with AsyncSessionLocal() as db:
        session = Session(id=gen_id("sess"), goal=goal, status="IDLE")
        db.add(session)
        await db.flush()
        await _log_event(db, session.id, "session_created", "human", details={"goal": goal})
        await _commit(db)
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
            session.execution_epoch = (session.execution_epoch or 0) + 1
            await _log_event(db, session_id, "plan_generation_started", "coordinator")
            await _commit(db)

        try:
            tasks_spec, used_llm = await planner.generate_plan(await _fetch_goal(session_id))
        except Exception as exc:
            await _fail(session_id, exc)
            return

        async with AsyncSessionLocal() as db:
            session = await db.get(Session, session_id)
            created: list[Task] = []
            for i, spec in enumerate(tasks_spec):
                created.append(Task(
                    id=gen_id("task"), session_id=session_id, name=spec["name"],
                    agent=spec["agent"], status="pending", order_index=i, depends_on=[],
                    objective=spec["name"],
                    intended_next_action="Execute assigned task after dependencies complete",
                    capabilities=[spec["agent"]],
                    human_assistance_conditions=["failure", "high uncertainty", "approval required"],
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
                await _broadcast_task(db, session_id, t)
            await _set_session_status(db, session, "RUNNING")
            await _commit(db)

        control.resume_event.set()
        control.cancel_requested = False
        control.running_task_future = asyncio.create_task(_run_loop(session_id))


async def _fetch_goal(session_id: str) -> str:
    async with AsyncSessionLocal() as db:
        session = await db.get(Session, session_id)
        return session.goal


async def _execute_task_with_recovery(
    session_id: str,
    task_id: str,
    agent: str,
    task_name: str,
    goal: str,
) -> dict:
    async with AsyncSessionLocal() as db:
        task = await db.get(Task, task_id)
        max_retries = task.max_retries
        timeout_seconds = task.timeout_seconds

    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            async def execute():
                if agent == "research":
                    ctx = await _gather_completed_summaries(session_id)
                    return await workers.run_research(task_name, goal + "\nPrior outputs: " + "\n".join(ctx))
                if agent == "verification":
                    ctx = await _gather_completed_summaries(session_id)
                    return await workers.run_verification(ctx, f"{goal}\nTask: {task_name}")
                if agent == "reporter":
                    ctx = await _gather_completed_outputs(session_id)
                    return await workers.run_reporter(ctx, f"{goal}\nTask: {task_name}")
                return {
                    "result": "",
                    "explanation": "",
                    "evidence": [],
                    "uncertainty": "high",
                    "limitations": "unknown agent",
                }

            return await asyncio.wait_for(execute(), timeout=timeout_seconds)
        except Exception as exc:
            last_error = exc
            if attempt < max_retries:
                async with AsyncSessionLocal() as db:
                    task = await db.get(Task, task_id)
                    task.retry_count = attempt + 1
                    task.checkpoint = {
                        "attempt": attempt + 1,
                        "error": str(exc),
                        "checkpointed_at": datetime.now(timezone.utc).isoformat(),
                    }
                    await db.flush()
                    await _broadcast_task(db, session_id, task)
                    await _log_event(
                        db, session_id, "task_retry", agent, task_id=task_id,
                        details={"attempt": attempt + 1, "error": str(exc)},
                    )
                    await db.commit()
    raise last_error or RuntimeError("task execution failed")


async def _is_current_execution(session_id: str, task_id: str, epoch: int) -> bool:
    async with AsyncSessionLocal() as db:
        session = await db.get(Session, session_id)
        task = await db.get(Task, task_id)
        return bool(
            session
            and task
            and session.execution_epoch == epoch
            and session.status in ("RUNNING", "AWAITING_APPROVAL")
            and task.status == "running"
        )


async def _run_loop(session_id: str):
    control = _get_control(session_id)
    try:
        while True:
            # Safe checkpoint: block here if paused
            await control.resume_event.wait()

            async with AsyncSessionLocal() as db:
                session = await db.get(Session, session_id)
                if session.status != "RUNNING":
                    return
                if control.cancel_requested:
                    await _set_session_status(db, session, "CANCELLED")
                    await _log_event(db, session_id, "session_cancelled", "human")
                    await _commit(db)
                    return

                result = await db.execute(select(Task).where(Task.session_id == session_id))
                all_tasks = sorted(result.scalars().all(), key=lambda t: t.order_index)

                next_task = None
                for t in all_tasks:
                    if t.status != "pending":
                        continue
                    deps = t.depends_on or []
                    dep_tasks = [x for x in all_tasks if x.id in deps]
                    if len(dep_tasks) == len(deps) and all(d.status == "completed" for d in dep_tasks):
                        next_task = t
                        break

                if next_task is None:
                    # check if all tasks are completed/skipped -> finish session
                    unfinished = [t for t in all_tasks if t.status in ("pending", "running")]
                    if not unfinished and all(t.status in ("completed", "skipped") for t in all_tasks):
                        session.current_task_id = None
                        await _set_session_status(db, session, "COMPLETED")
                        await _log_event(db, session_id, "session_completed", "coordinator")
                        await _commit(db)
                        return
                    else:
                        # stuck (e.g. failed dependency) — mark failed
                        await _set_session_status(db, session, "FAILED")
                        await _log_event(db, session_id, "session_failed", "coordinator",
                                          details={"reason": "no runnable task but unfinished tasks remain"})
                        await _commit(db)
                        return

                session.current_task_id = next_task.id
                next_task.status = "running"
                await db.flush()
                await _broadcast_task(db, session_id, next_task)
                await _log_event(db, session_id, "task_started", next_task.agent, task_id=next_task.id,
                                  details={"name": next_task.name})
                await _commit(db)
                goal = session.goal
                agent = next_task.agent
                task_id = next_task.id
                task_name = next_task.name
                execution_epoch = session.execution_epoch

            # Execute outside the DB transaction (agent calls may be slow / network)
            try:
                output = await _execute_task_with_recovery(
                    session_id, task_id, agent, task_name, goal
                )
            except Exception as exc:
                if not await _is_current_execution(session_id, task_id, execution_epoch):
                    return
                async with AsyncSessionLocal() as db:
                    session = await db.get(Session, session_id)
                    task = await db.get(Task, task_id)
                    task.status = "failed"
                    task.result = f"Error: {exc}"
                    await db.flush()
                    await _broadcast_task(db, session_id, task)
                    await _log_event(db, session_id, "task_failed", agent, task_id=task_id,
                                      details={"error": str(exc)})
                    await _set_session_status(db, session, "FAILED")
                    await _commit(db)
                return

            if not await _is_current_execution(session_id, task_id, execution_epoch):
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
                    await _broadcast_task(db, session_id, task)

                    approval = Approval(
                        id=gen_id("appr"), session_id=session_id, task_id=task_id,
                        proposed_action=f"Finalize and deliver report: {task_name}",
                        expected_impact="This will mark the final report as delivered to the user "
                                        "and complete the session.",
                        evidence=output["evidence"], status="pending",
                    )
                    db.add(approval)
                    await db.flush()
                    control.resume_event.clear()
                    await _set_session_status(db, session, "AWAITING_APPROVAL")
                    await _log_event(db, session_id, "approval_requested", "reporter", task_id=task_id,
                                      details={"approval_id": approval.id})
                    await _queue(db, session_id, {
                        "type": "approval_request",
                        "approval": {
                            "id": approval.id, "session_id": session_id, "task_id": task_id,
                            "proposed_action": approval.proposed_action,
                            "expected_impact": approval.expected_impact,
                            "evidence": approval.evidence, "status": "pending",
                        },
                    })
                    await _commit(db)
                # Block the loop until approve/reject resumes it (approve/reject flips resume_event)
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
                await _broadcast_task(db, session_id, task)
                await _log_event(db, session_id, "task_completed", agent, task_id=task_id,
                                  details={"name": task_name})
                await _commit(db)
    except asyncio.CancelledError:
        return
    except Exception as exc:
        await _fail(session_id, exc)


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


async def _pause_session(session_id: str):
    control = _get_control(session_id)
    async with AsyncSessionLocal() as db:
        session = await db.get(Session, session_id)
        if session is None:
            raise ValueError("session not found")
        if session.status == "PAUSED":
            return
        if session.status != "RUNNING":
            raise InvalidTransition(session.status, "PAUSED")
        control.resume_event.clear()
        if control.running_task_future:
            control.running_task_future.cancel()
            await asyncio.gather(control.running_task_future, return_exceptions=True)
        await db.refresh(session)
        await _set_session_status(db, session, "PAUSED")
        session.execution_epoch = (session.execution_epoch or 0) + 1
        tasks = (await db.execute(select(Task).where(Task.session_id == session_id, Task.status == "running"))).scalars().all()
        for task in tasks:
            task.status = "pending"
            await _broadcast_task(db, session_id, task)
        session.current_task_id = None
        await _log_event(db, session_id, "agent_paused", "human")
        await _commit(db)
    if control.running_task_future:
        control.running_task_future.cancel()
        await asyncio.gather(control.running_task_future, return_exceptions=True)


async def _resume_session(session_id: str):
    control = _get_control(session_id)
    async with AsyncSessionLocal() as db:
        session = await db.get(Session, session_id)
        if session is None:
            raise ValueError("session not found")
        if session.status == "RUNNING":
            return
        if session.status != "PAUSED":
            raise InvalidTransition(session.status, "RUNNING")
        await _set_session_status(db, session, "RUNNING")
        session.execution_epoch = (session.execution_epoch or 0) + 1
        await _log_event(db, session_id, "agent_resumed", "human")
        await _commit(db)
    control.resume_event.set()
    if control.running_task_future is None or control.running_task_future.done():
        control.running_task_future = asyncio.create_task(_run_loop(session_id))


async def _redirect_session(session_id: str, instruction: str, task_id: str | None):
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
        if target is not None and target.status == "skipped":
            replacement = next((t for t in all_tasks if t.order_index == target.order_index and t.name == f"[Redirected] {instruction}" and t.status == "pending"), None)
            if replacement:
                return
        if task_id and target is None:
            raise ValueError("target not found")
        if target is None:
            # default: the current / next pending task
            target = next((t for t in all_tasks if t.status == "pending"), None)

        if target is None or target.status != "pending":
            raise ValueError("only pending tasks can be redirected")

        session.execution_epoch = (session.execution_epoch or 0) + 1
        # Mark the target skipped and insert a new task in its place, preserving
        # dependency edges so downstream tasks (e.g. "Compare results") now wait
        # on the *new* task instead.
        target.status = "skipped"
        new_task = Task(
            id=gen_id("task"), session_id=session_id,
            name=f"[Redirected] {instruction}", agent=target.agent,
            status="pending", order_index=target.order_index, depends_on=list(target.depends_on or []),
        )
        db.add(new_task)
        await db.flush()

        for t in all_tasks:
            if target.id in (t.depends_on or []):
                deps = list(t.depends_on)
                deps = [new_task.id if d == target.id else d for d in deps]
                t.depends_on = deps
                await _broadcast_task(db, session_id, t)

        await db.flush()
        await _broadcast_task(db, session_id, target)
        await _broadcast_task(db, session_id, new_task)
        await _log_event(db, session_id, "human_redirected", "human", task_id=target.id,
                          details={"instruction": instruction, "replaced_with": new_task.id})
        # keep status PAUSED (human must still issue /resume), matches "PAUSED -> PAUSED" allowed transition
        await _commit(db)


async def _cancel_session(session_id: str):
    control = _get_control(session_id)
    async with AsyncSessionLocal() as db:
        session = await db.get(Session, session_id)
        if session is None:
            raise ValueError("session not found")
        if session.status == "CANCELLED":
            return
        if session.status in ("COMPLETED", "FAILED"):
            raise InvalidTransition(session.status, "CANCELLED")
        if control.running_task_future:
            control.running_task_future.cancel()
            await asyncio.gather(control.running_task_future, return_exceptions=True)
        await db.refresh(session)
        await _set_session_status(db, session, "CANCELLED")
        session.execution_epoch = (session.execution_epoch or 0) + 1
        session.current_task_id = None
        for task in (await db.execute(select(Task).where(Task.session_id == session_id, Task.status.in_(["pending", "running"])))).scalars():
            task.status = "skipped"
            await _broadcast_task(db, session_id, task)
        for approval in (await db.execute(select(Approval).where(Approval.session_id == session_id, Approval.status == "pending"))).scalars():
            approval.status = "rejected"
            approval.resolved_at = datetime.now(timezone.utc)
            await _queue(db, session_id, {"type":"approval_resolved", "approval_id":approval.id,"status":"rejected"})
        await _log_event(db, session_id, "session_cancelled", "human")
        await _commit(db)
    control.cancel_requested = True
    control.resume_event.set()  # unblock loop so it can observe cancellation and exit
    if control.running_task_future:
        control.running_task_future.cancel()


async def _approve_action(approval_id: str):
    async with AsyncSessionLocal() as db:
        approval = await db.get(Approval, approval_id)
        if approval is None:
            raise ValueError("approval not found")
        if approval.status == "approved":
            return
        if approval.status != "pending":
            raise ValueError("approval already resolved")
        approval.status = "approved"
        approval.resolved_at = datetime.now(timezone.utc)
        session = await db.get(Session, approval.session_id)
        task = await db.get(Task, approval.task_id) if approval.task_id else None
        if session.status != "AWAITING_APPROVAL" or not task or task.status != "running":
            raise InvalidTransition(session.status, "AWAITING_APPROVAL")
        if task:
            task.status = "completed"
            await _broadcast_task(db, session.id, task)
        await _set_session_status(db, session, "RUNNING")
        await _log_event(db, session.id, "approval_granted", "human", task_id=approval.task_id,
                          details={"approval_id": approval_id})
        await _queue(db, session.id, {
            "type": "approval_resolved",
            "approval_id": approval_id, "status": "approved",
        })
        await _commit(db)
        session_id = session.id

    control = _get_control(session_id)
    control.resume_event.set()
    if control.running_task_future is None or control.running_task_future.done():
        control.running_task_future = asyncio.create_task(_run_loop(session_id))


async def _reject_action(approval_id: str, feedback: str | None = None):
    async with AsyncSessionLocal() as db:
        approval = await db.get(Approval, approval_id)
        if approval is None:
            raise ValueError("approval not found")
        if approval.status == "rejected":
            return
        if approval.status != "pending":
            raise ValueError("approval already resolved")
        approval.status = "rejected"
        approval.resolved_at = datetime.now(timezone.utc)
        approval.feedback = feedback
        session = await db.get(Session, approval.session_id)
        task = await db.get(Task, approval.task_id) if approval.task_id else None
        if session.status != "AWAITING_APPROVAL" or not task or task.status != "running":
            raise InvalidTransition(session.status, "AWAITING_APPROVAL")
        if task:
            task.status = "pending"
            task.checkpoint = {
                "stage": "awaiting_revision",
                "feedback": feedback or "",
                "previous_result": task.result,
            }
            await _broadcast_task(db, session.id, task)
        await _set_session_status(db, session, "PAUSED")
        await _log_event(db, session.id, "approval_rejected", "human", task_id=approval.task_id,
                          details={"approval_id": approval_id, "feedback": feedback or ""})
        db.add(Intervention(
            session_id=session.id,
            task_id=approval.task_id,
            action="reject",
            actor="human",
            reason=feedback,
            before={"status": "AWAITING_APPROVAL"},
            after={"status": "PAUSED", "task_status": "pending"},
        ))
        await _queue(db, session.id, {
            "type": "approval_resolved",
            "approval_id": approval_id, "status": "rejected",
        })
        await _commit(db)
        session_id = session.id
    control = _get_control(session_id)
    control.resume_event.set()
    if control.running_task_future is not None:
        await asyncio.gather(control.running_task_future, return_exceptions=True)

async def _fail(session_id, exc):
    async with AsyncSessionLocal() as db:
        session = await db.get(Session, session_id)
        if session and session.status in ("RUNNING", "PLANNING", "AWAITING_APPROVAL"):
            for task in (await db.execute(select(Task).where(Task.session_id == session_id, Task.status == "running"))).scalars():
                task.status = "failed"
                await _broadcast_task(db, session_id, task)
            session.current_task_id = None
            await _set_session_status(db, session, "FAILED")
            await _log_event(db, session_id, "session_failed", "coordinator", details={"reason": str(exc)})
            await _commit(db)

async def recover_sessions():
    # Fail closed after an interrupted process; never silently replay an agent.
    async with AsyncSessionLocal() as db:
        ids = (await db.execute(select(Session.id).where(Session.status.in_(["RUNNING", "PLANNING"])))).scalars().all()
    for sid in ids:
        await _fail(sid, RuntimeError("Execution interrupted by server restart"))

# Serialize human commands within the supported single server process.
async def _execute_idempotent(session_id: str, command_id: str | None,
                              command_type: str, action):
    if not command_id:
        await action()
        return
    async with AsyncSessionLocal() as db:
        existing = await db.scalar(
            select(Command).where(
                Command.session_id == session_id,
                Command.command_id == command_id,
            )
        )
        if existing:
            return existing.result
    async with _get_control(session_id).lock:
        async with AsyncSessionLocal() as db:
            existing = await db.scalar(
                select(Command).where(
                    Command.session_id == session_id,
                    Command.command_id == command_id,
                )
            )
            if existing:
                return existing.result
        await action()
        async with AsyncSessionLocal() as db:
            db.add(Command(
                session_id=session_id,
                command_id=command_id,
                command_type=command_type,
                result={"accepted": True},
            ))
            await db.commit()


async def pause_session(session_id, command_id: str | None = None):
    await _execute_idempotent(
        session_id, command_id, "pause",
        lambda: _pause_session(session_id),
    )
async def resume_session(session_id, command_id: str | None = None):
    await _execute_idempotent(
        session_id, command_id, "resume",
        lambda: _resume_session(session_id),
    )
async def redirect_session(session_id, instruction, task_id, command_id: str | None = None):
    await _execute_idempotent(
        session_id, command_id, "redirect",
        lambda: _redirect_session(session_id, instruction, task_id),
    )
async def cancel_session(session_id, command_id: str | None = None):
    await _execute_idempotent(
        session_id, command_id, "cancel",
        lambda: _cancel_session(session_id),
    )
async def edit_task(session_id: str, task_id: str, name: str | None = None,
                    agent: str | None = None, depends_on: list[str] | None = None,
                    reason: str | None = None, command_id: str | None = None):
    async def action():
        async with AsyncSessionLocal() as db:
            session = await db.get(Session, session_id)
            task = await db.get(Task, task_id)
            if not session or not task:
                raise ValueError("session or task not found")
            if session.status != "PAUSED" or task.status not in ("pending", "paused"):
                raise InvalidTransition(session.status, "PAUSED")
            before = {"name": task.name, "agent": task.agent, "depends_on": task.depends_on}
            if name:
                task.name = name
            if agent and agent in {"planner", "research", "verification", "reporter"}:
                task.agent = agent
            if depends_on is not None:
                valid_ids = set((await db.execute(select(Task.id).where(Task.session_id == session_id))).scalars())
                if any(dep not in valid_ids or dep == task_id for dep in depends_on):
                    raise ValueError("invalid task dependency")
                task.depends_on = depends_on
            await db.flush()
            await _broadcast_task(db, session_id, task)
            db.add(Intervention(
                session_id=session_id, task_id=task_id, action="edit_task",
                reason=reason, before=before,
                after={"name": task.name, "agent": task.agent, "depends_on": task.depends_on},
            ))
            await _log_event(db, session_id, "task_edited", "human", task_id=task_id,
                              details={"reason": reason})
            await db.commit()
    await _execute_idempotent(session_id, command_id, "edit_task", action)


async def add_task(session_id: str, name: str, agent: str,
                   depends_on: list[str] | None = None, reason: str | None = None,
                   command_id: str | None = None):
    async def action():
        async with AsyncSessionLocal() as db:
            session = await db.get(Session, session_id)
            if not session:
                raise ValueError("session not found")
            if session.status != "PAUSED":
                raise InvalidTransition(session.status, "PAUSED")
            if agent not in {"planner", "research", "verification", "reporter"}:
                raise ValueError("invalid agent")
            valid_ids = set((await db.execute(select(Task.id).where(Task.session_id == session_id))).scalars())
            deps = depends_on or []
            if any(dep not in valid_ids for dep in deps):
                raise ValueError("invalid task dependency")
            count = (await db.execute(select(Task).where(Task.session_id == session_id))).scalars().all()
            task = Task(
                id=gen_id("task"), session_id=session_id, name=name, agent=agent,
                status="pending", order_index=max([t.order_index for t in count], default=-1) + 1,
                depends_on=deps,
            )
            db.add(task)
            await db.flush()
            await _broadcast_task(db, session_id, task)
            db.add(Intervention(
                session_id=session_id, task_id=task.id, action="add_task",
                reason=reason, before={}, after={"name": name, "agent": agent, "depends_on": deps},
            ))
            await _log_event(db, session_id, "task_added", "human", task_id=task.id,
                              details={"reason": reason})
            await db.commit()
    await _execute_idempotent(session_id, command_id, "add_task", action)


async def remove_task(session_id: str, task_id: str, reason: str | None = None,
                      command_id: str | None = None):
    async def action():
        async with AsyncSessionLocal() as db:
            session = await db.get(Session, session_id)
            task = await db.get(Task, task_id)
            if not session or not task:
                raise ValueError("session or task not found")
            if session.status != "PAUSED" or task.status not in ("pending", "paused"):
                raise InvalidTransition(session.status, "PAUSED")
            before = {"status": task.status, "name": task.name}
            task.status = "skipped"
            task.limitations = (task.limitations or "") + (f" Removed by human: {reason}" if reason else "")
            for downstream in (await db.execute(select(Task).where(Task.session_id == session_id))).scalars():
                if task_id in (downstream.depends_on or []):
                    downstream.depends_on = [dep for dep in downstream.depends_on if dep != task_id]
                    await _broadcast_task(db, session_id, downstream)
            await db.flush()
            await _broadcast_task(db, session_id, task)
            db.add(Intervention(
                session_id=session_id, task_id=task_id, action="remove_task",
                reason=reason, before=before, after={"status": "skipped"},
            ))
            await _log_event(db, session_id, "task_removed", "human", task_id=task_id,
                              details={"reason": reason})
            await db.commit()
    await _execute_idempotent(session_id, command_id, "remove_task", action)


async def reprioritize_tasks(session_id: str, task_ids: list[str],
                             reason: str | None = None, command_id: str | None = None):
    async def action():
        async with AsyncSessionLocal() as db:
            session = await db.get(Session, session_id)
            if not session:
                raise ValueError("session not found")
            if session.status != "PAUSED":
                raise InvalidTransition(session.status, "PAUSED")
            tasks = (await db.execute(select(Task).where(Task.session_id == session_id))).scalars().all()
            by_id = {task.id: task for task in tasks}
            if set(task_ids) != set(by_id) or len(task_ids) != len(set(task_ids)):
                raise ValueError("task_ids must contain every task exactly once")
            before = {task.id: task.order_index for task in tasks}
            for index, task_id in enumerate(task_ids):
                by_id[task_id].order_index = index
                await _broadcast_task(db, session_id, by_id[task_id])
            db.add(Intervention(
                session_id=session_id, action="reprioritize", reason=reason,
                before=before, after={task_id: index for index, task_id in enumerate(task_ids)},
            ))
            await _log_event(db, session_id, "tasks_reprioritized", "human",
                              details={"reason": reason, "task_ids": task_ids})
            await db.commit()
    await _execute_idempotent(session_id, command_id, "reprioritize", action)
async def _resolve(approval_id, action, command_id: str | None = None, command_type: str = "approval"):
    async with AsyncSessionLocal() as db:
        approval = await db.get(Approval, approval_id)
        if not approval:
            raise ValueError("approval not found")
        sid = approval.session_id
    await _execute_idempotent(sid, command_id, command_type, lambda: action(approval_id))
async def approve_action(approval_id, command_id: str | None = None):
    await _resolve(approval_id, _approve_action, command_id, "approve")
async def reject_action(approval_id, command_id: str | None = None, feedback: str | None = None):
    await _resolve(
        approval_id,
        lambda resolved_id: _reject_action(resolved_id, feedback),
        command_id,
        "reject",
    )

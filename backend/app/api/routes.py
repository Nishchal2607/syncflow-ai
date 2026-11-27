from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.db import get_db, AsyncSessionLocal
from app.database.models import Session, Approval, Event, Intervention
from app.schemas.schemas import (
    SessionCreateRequest, SessionOut, RedirectRequest, ApprovalOut, EventOut, HealthOut,
    CommandRequest, TaskMutationRequest, ReprioritizeRequest, InterventionOut,
)
from app.orchestration import coordinator
from app.orchestration.state_machine import InvalidTransition
from app.agents.llm_client import is_live
from app.interaction.ws_manager import manager

router = APIRouter()


@router.get("/api/health", response_model=HealthOut)
async def health():
    return HealthOut(status="ok", mode="llm" if is_live() else "deterministic_fallback")


@router.post("/api/sessions", response_model=SessionOut)
async def create_session(req: SessionCreateRequest):
    session = await coordinator.create_session(req.goal)
    return SessionOut(
        id=session.id, goal=session.goal, status=session.status,
        current_task_id=session.current_task_id,
        created_at=session.created_at, updated_at=session.updated_at, tasks=[],
    )


async def _load_session(db: AsyncSession, session_id: str) -> Session:
    result = await db.execute(
        select(Session).options(selectinload(Session.tasks)).where(Session.id == session_id)
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    return session


@router.post("/api/sessions/{session_id}/start", response_model=SessionOut)
async def start_session(session_id: str, db: AsyncSession = Depends(get_db)):
    try:
        await coordinator.start_session(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidTransition as e:
        raise HTTPException(status_code=409, detail=str(e))
    session = await _load_session(db, session_id)
    return session


@router.get("/api/sessions/{session_id}", response_model=SessionOut)
async def get_session(session_id: str, db: AsyncSession = Depends(get_db)):
    session = await _load_session(db, session_id)
    return session


@router.post("/api/sessions/{session_id}/pause", response_model=SessionOut)
async def pause(session_id: str, req: CommandRequest = CommandRequest(), db: AsyncSession = Depends(get_db)):
    try:
        await coordinator.pause_session(session_id, req.command_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidTransition as e:
        raise HTTPException(status_code=409, detail=str(e))
    return await _load_session(db, session_id)


@router.post("/api/sessions/{session_id}/resume", response_model=SessionOut)
async def resume(session_id: str, req: CommandRequest = CommandRequest(), db: AsyncSession = Depends(get_db)):
    try:
        await coordinator.resume_session(session_id, req.command_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidTransition as e:
        raise HTTPException(status_code=409, detail=str(e))
    return await _load_session(db, session_id)


@router.post("/api/sessions/{session_id}/redirect", response_model=SessionOut)
async def redirect(session_id: str, req: RedirectRequest, db: AsyncSession = Depends(get_db)):
    try:
        await coordinator.redirect_session(session_id, req.instruction, req.task_id, req.command_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidTransition as e:
        raise HTTPException(
            status_code=409,
            detail=f"{e} — redirect requires the session to be PAUSED first.",
        )
    return await _load_session(db, session_id)


@router.patch("/api/sessions/{session_id}/tasks/{task_id}", response_model=SessionOut)
async def edit_task(session_id: str, task_id: str, req: TaskMutationRequest,
                    db: AsyncSession = Depends(get_db)):
    try:
        await coordinator.edit_task(
            session_id, task_id, req.name, req.agent, req.depends_on, req.reason, req.command_id
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidTransition as e:
        raise HTTPException(status_code=409, detail=str(e))
    return await _load_session(db, session_id)


@router.post("/api/sessions/{session_id}/tasks", response_model=SessionOut)
async def add_task(session_id: str, req: TaskMutationRequest,
                   db: AsyncSession = Depends(get_db)):
    if not req.name or not req.agent:
        raise HTTPException(status_code=422, detail="name and agent are required")
    try:
        await coordinator.add_task(
            session_id, req.name, req.agent, req.depends_on, req.reason, req.command_id
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidTransition as e:
        raise HTTPException(status_code=409, detail=str(e))
    return await _load_session(db, session_id)


@router.delete("/api/sessions/{session_id}/tasks/{task_id}", response_model=SessionOut)
async def remove_task(session_id: str, task_id: str, req: TaskMutationRequest = TaskMutationRequest(),
                      db: AsyncSession = Depends(get_db)):
    try:
        await coordinator.remove_task(session_id, task_id, req.reason, req.command_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidTransition as e:
        raise HTTPException(status_code=409, detail=str(e))
    return await _load_session(db, session_id)


@router.post("/api/sessions/{session_id}/reprioritize", response_model=SessionOut)
async def reprioritize(session_id: str, req: ReprioritizeRequest,
                       db: AsyncSession = Depends(get_db)):
    try:
        await coordinator.reprioritize_tasks(
            session_id, req.task_ids, req.reason, req.command_id
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidTransition as e:
        raise HTTPException(status_code=409, detail=str(e))
    return await _load_session(db, session_id)


@router.get("/api/sessions/{session_id}/interventions", response_model=list[InterventionOut])
async def get_interventions(session_id: str, db: AsyncSession = Depends(get_db)):
    await _load_session(db, session_id)
    result = await db.execute(
        select(Intervention).where(Intervention.session_id == session_id)
        .order_by(Intervention.created_at.asc())
    )
    return result.scalars().all()


@router.post("/api/sessions/{session_id}/cancel", response_model=SessionOut)
async def cancel(session_id: str, req: CommandRequest = CommandRequest(), db: AsyncSession = Depends(get_db)):
    try:
        await coordinator.cancel_session(session_id, req.command_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidTransition as e:
        raise HTTPException(status_code=409, detail=str(e))
    return await _load_session(db, session_id)


@router.post("/api/approvals/{approval_id}/approve", response_model=ApprovalOut)
async def approve(approval_id: str, req: CommandRequest = CommandRequest(), db: AsyncSession = Depends(get_db)):
    try:
        await coordinator.approve_action(approval_id, req.command_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidTransition as e:
        raise HTTPException(status_code=409, detail=str(e))
    approval = await db.get(Approval, approval_id)
    return approval


@router.post("/api/approvals/{approval_id}/reject", response_model=ApprovalOut)
async def reject(approval_id: str, req: CommandRequest = CommandRequest(), db: AsyncSession = Depends(get_db)):
    try:
        await coordinator.reject_action(approval_id, req.command_id, req.feedback)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidTransition as e:
        raise HTTPException(status_code=409, detail=str(e))
    approval = await db.get(Approval, approval_id)
    return approval


@router.get("/api/sessions/{session_id}/approvals", response_model=list[ApprovalOut])
async def get_approvals(session_id: str, db: AsyncSession = Depends(get_db)):
    await _load_session(db, session_id)
    result = await db.execute(select(Approval).where(
        Approval.session_id == session_id, Approval.status == "pending"
    ).order_by(Approval.created_at.asc(), Approval.id.asc()))
    return result.scalars().all()


@router.get("/api/sessions/{session_id}/events", response_model=list[EventOut])
async def get_events(session_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Event).where(Event.session_id == session_id).order_by(Event.timestamp.asc())
    )
    return result.scalars().all()


@router.websocket("/ws/sessions/{session_id}")
async def ws_session(websocket: WebSocket, session_id: str):
    await manager.connect(session_id, websocket)
    try:
        async with AsyncSessionLocal() as db:
            session = await db.get(Session, session_id)
            if session is None:
                await websocket.close(code=4404)
                return
            event_result = await db.execute(
                select(Event).where(Event.session_id == session_id).order_by(Event.sequence.asc())
            )
            events = event_result.scalars().all()
            approval_result = await db.execute(
                select(Approval).where(
                    Approval.session_id == session_id,
                    Approval.status == "pending",
                ).order_by(Approval.created_at.asc())
            )
            approvals = approval_result.scalars().all()
        await websocket.send_json({
            "type": "snapshot",
            "sequence": events[-1].sequence if events else 0,
            "session": {
                "id": session.id,
                "status": session.status,
                "current_task_id": session.current_task_id,
                "execution_epoch": session.execution_epoch,
            },
            "events": [
                {
                    "id": event.id,
                    "session_id": event.session_id,
                    "event_type": event.event_type,
                    "actor": event.actor,
                    "task_id": event.task_id,
                    "details": event.details or {},
                    "timestamp": event.timestamp.isoformat(),
                    "sequence": event.sequence,
                }
                for event in events
            ],
            "pending_approvals": [
                {
                    "id": approval.id,
                    "session_id": approval.session_id,
                    "task_id": approval.task_id,
                    "proposed_action": approval.proposed_action,
                    "expected_impact": approval.expected_impact,
                    "evidence": approval.evidence or [],
                    "status": approval.status,
                    "created_at": approval.created_at.isoformat(),
                    "resolved_at": approval.resolved_at.isoformat() if approval.resolved_at else None,
                }
                for approval in approvals
            ],
        })
        while True:
            # We don't expect inbound messages, but keep the socket alive.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(session_id, websocket)

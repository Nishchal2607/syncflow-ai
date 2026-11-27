from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.db import get_db
from app.database.models import Session, Approval, Event
from app.schemas.schemas import (
    SessionCreateRequest, SessionOut, RedirectRequest, ApprovalOut, EventOut, HealthOut,
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
async def pause(session_id: str, db: AsyncSession = Depends(get_db)):
    try:
        await coordinator.pause_session(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidTransition as e:
        raise HTTPException(status_code=409, detail=str(e))
    return await _load_session(db, session_id)


@router.post("/api/sessions/{session_id}/resume", response_model=SessionOut)
async def resume(session_id: str, db: AsyncSession = Depends(get_db)):
    try:
        await coordinator.resume_session(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidTransition as e:
        raise HTTPException(status_code=409, detail=str(e))
    return await _load_session(db, session_id)


@router.post("/api/sessions/{session_id}/redirect", response_model=SessionOut)
async def redirect(session_id: str, req: RedirectRequest, db: AsyncSession = Depends(get_db)):
    try:
        await coordinator.redirect_session(session_id, req.instruction, req.task_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidTransition as e:
        raise HTTPException(
            status_code=409,
            detail=f"{e} — redirect requires the session to be PAUSED first.",
        )
    return await _load_session(db, session_id)


@router.post("/api/sessions/{session_id}/cancel", response_model=SessionOut)
async def cancel(session_id: str, db: AsyncSession = Depends(get_db)):
    try:
        await coordinator.cancel_session(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidTransition as e:
        raise HTTPException(status_code=409, detail=str(e))
    return await _load_session(db, session_id)


@router.post("/api/approvals/{approval_id}/approve", response_model=ApprovalOut)
async def approve(approval_id: str, db: AsyncSession = Depends(get_db)):
    try:
        await coordinator.approve_action(approval_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidTransition as e:
        raise HTTPException(status_code=409, detail=str(e))
    approval = await db.get(Approval, approval_id)
    return approval


@router.post("/api/approvals/{approval_id}/reject", response_model=ApprovalOut)
async def reject(approval_id: str, db: AsyncSession = Depends(get_db)):
    try:
        await coordinator.reject_action(approval_id)
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
        while True:
            # We don't expect inbound messages, but keep the socket alive.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(session_id, websocket)

"""
Integration tests for the SyncFlow AI coordinator/state machine.

Run with: pytest -q  (from backend/)
These run in deterministic fallback mode (no API key needed) and use a
near-zero simulated work delay so the suite is fast, while still exercising
real asyncio concurrency (pause/redirect/resume race conditions).
"""
import os
os.environ["SYNCFLOW_SIMULATED_WORK_SECONDS"] = "0.2"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_syncflow.db"

import asyncio
import pytest
import pytest_asyncio

from app.database.db import init_db, AsyncSessionLocal, engine
from app.database.models import Base, Task
from app.orchestration import coordinator
from app.orchestration.state_machine import can_transition, InvalidTransition
from sqlalchemy import select


@pytest_asyncio.fixture(autouse=True)
async def _fresh_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield
    finally:
        # Drain coordinator tasks before pytest closes this test's event loop.
        futures = [c.running_task_future for c in coordinator._controls.values()
                   if c.running_task_future is not None]
        for future in futures:
            if not future.done():
                future.cancel()
        try:
            if futures:
                await asyncio.gather(*futures, return_exceptions=True)
        finally:
            coordinator._controls.clear()
            await engine.dispose()


async def _poll_status(session_id, target, timeout=10):
    from app.database.models import Session
    for _ in range(int(timeout / 0.1)):
        async with AsyncSessionLocal() as db:
            s = await db.get(Session, session_id)
            if s.status == target:
                return s
        await asyncio.sleep(0.1)
    raise AssertionError(f"session never reached {target}")


def test_state_machine_rules():
    assert can_transition("IDLE", "PLANNING")
    assert not can_transition("IDLE", "RUNNING")
    assert can_transition("RUNNING", "PAUSED")
    assert not can_transition("PAUSED", "AWAITING_APPROVAL")
    assert can_transition("PAUSED", "RUNNING")
    assert not can_transition("COMPLETED", "RUNNING")


@pytest.mark.asyncio
async def test_full_happy_path_reaches_approval_and_completes():
    session = await coordinator.create_session("Research two EV companies and report.")
    await coordinator.start_session(session.id)

    s = await _poll_status(session.id, "AWAITING_APPROVAL")
    assert s.status == "AWAITING_APPROVAL"

    from app.database.models import Approval
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Approval).where(Approval.session_id == session.id))
        approval = result.scalars().first()
    assert approval.status == "pending"

    await coordinator.approve_action(approval.id)
    s = await _poll_status(session.id, "COMPLETED")
    assert s.status == "COMPLETED"


@pytest.mark.asyncio
async def test_pause_then_redirect_mutates_graph_and_resume_completes():
    session = await coordinator.create_session("Research three EV companies and report.")
    await coordinator.start_session(session.id)
    await asyncio.sleep(0.05)  # let the loop start the first task
    await coordinator.pause_session(session.id)

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Task).where(Task.session_id == session.id))
        tasks = sorted(result.scalars().all(), key=lambda t: t.order_index)
    target = next(t for t in tasks if t.agent == "research" and t.status == "pending")

    await coordinator.redirect_session(session.id, "swap this subject out", target.id)

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Task).where(Task.session_id == session.id))
        tasks_after = result.scalars().all()
    skipped = [t for t in tasks_after if t.id == target.id][0]
    assert skipped.status == "skipped"
    assert any("[Redirected]" in t.name for t in tasks_after)

    await coordinator.resume_session(session.id)

    s = await _poll_status(session.id, "AWAITING_APPROVAL", timeout=15)
    assert s.status == "AWAITING_APPROVAL"

    from app.database.models import Approval
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Approval).where(Approval.session_id == session.id))
        approval = result.scalars().first()
    await coordinator.approve_action(approval.id)
    s = await _poll_status(session.id, "COMPLETED")
    assert s.status == "COMPLETED"


@pytest.mark.asyncio
async def test_redirect_rejected_when_not_paused():
    session = await coordinator.create_session("Research two EV companies and report.")
    await coordinator.start_session(session.id)
    with pytest.raises(InvalidTransition):
        await coordinator.redirect_session(session.id, "nope", None)
    await coordinator.cancel_session(session.id)


@pytest.mark.asyncio
async def test_cancel_stops_execution_permanently():
    session = await coordinator.create_session("Research two EV companies and report.")
    await coordinator.start_session(session.id)
    await asyncio.sleep(0.05)
    await coordinator.cancel_session(session.id)
    await asyncio.sleep(0.5)

    from app.database.models import Session as SessionModel
    async with AsyncSessionLocal() as db:
        s = await db.get(SessionModel, session.id)
    assert s.status == "CANCELLED"

    with pytest.raises(InvalidTransition):
        await coordinator.resume_session(session.id)


@pytest.mark.asyncio
async def test_rejection_marks_session_failed_not_completed():
    session = await coordinator.create_session("Research two EV companies and report.")
    await coordinator.start_session(session.id)
    s = await _poll_status(session.id, "AWAITING_APPROVAL")

    from app.database.models import Approval
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Approval).where(Approval.session_id == session.id))
        approval = result.scalars().first()
    await coordinator.reject_action(approval.id)

    s = await _poll_status(session.id, "FAILED")
    assert s.status == "FAILED"


@pytest.mark.asyncio
async def test_duplicate_start_does_not_duplicate_tasks():
    session = await coordinator.create_session("Research two EV companies and report.")
    await coordinator.start_session(session.id)
    await coordinator.start_session(session.id)  # duplicate call, should be a no-op
    await asyncio.sleep(0.1)

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Task).where(Task.session_id == session.id))
        tasks = result.scalars().all()
    names = [t.name for t in tasks]
    assert len(names) == len(set(names)), "duplicate start produced duplicate tasks"
    await coordinator.cancel_session(session.id)

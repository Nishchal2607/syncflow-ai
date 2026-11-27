import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from dotenv import load_dotenv

from app.database.models import Base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./syncflow.db")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_ensure_sqlite_columns)


def _ensure_sqlite_columns(conn):
    if not str(engine.url).startswith("sqlite"):
        return
    session_columns = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(sessions)").all()}
    task_columns = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(tasks)").all()}
    event_columns = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(events)").all()}
    approval_columns = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(approvals)").all()}
    if "execution_epoch" not in session_columns:
        conn.exec_driver_sql("ALTER TABLE sessions ADD COLUMN execution_epoch INTEGER NOT NULL DEFAULT 1")
    for name, definition in {
        "retry_count": "INTEGER NOT NULL DEFAULT 0",
        "max_retries": "INTEGER NOT NULL DEFAULT 2",
        "timeout_seconds": "INTEGER NOT NULL DEFAULT 30",
        "checkpoint": "JSON",
        "objective": "TEXT",
        "intended_next_action": "TEXT",
        "capabilities": "JSON",
        "human_assistance_conditions": "JSON",
    }.items():
        if name not in task_columns:
            conn.exec_driver_sql(f"ALTER TABLE tasks ADD COLUMN {name} {definition}")
    if "sequence" not in event_columns:
        conn.exec_driver_sql("ALTER TABLE events ADD COLUMN sequence INTEGER NOT NULL DEFAULT 0")
    if "feedback" not in approval_columns:
        conn.exec_driver_sql("ALTER TABLE approvals ADD COLUMN feedback TEXT")


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

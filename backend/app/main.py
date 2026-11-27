import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.database.db import init_db
from app.api.routes import router

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    from app.orchestration.coordinator import recover_sessions
    await recover_sessions()
    yield


app = FastAPI(title="SyncFlow AI", version="0.1.0", lifespan=lifespan)

origins = [os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

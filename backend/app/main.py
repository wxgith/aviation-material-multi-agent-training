from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import settings
from app.services.task_manager import task_manager


@asynccontextmanager
async def lifespan(_app: FastAPI):
    task_manager.recover_after_restart()
    yield

app = FastAPI(
    title="航空工程材料损伤分析多智能体训练系统",
    description="面向航空工程材料技能培训的 RAG 个性化生成、多智能体协同决策与启发式追问系统。",
    version=settings.version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok", "message": "Aero Materials Training API"}

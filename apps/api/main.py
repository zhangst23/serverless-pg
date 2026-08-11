"""CloudPG Control Plane — FastAPI 应用入口。"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.config import settings
from apps.api.routers import (
    auth,
    backups,
    computes,
    databases,
    endpoints,
    metrics,
    projects,
    roles,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时确保 Control Plane DB 表存在 (MVP)
    from db.init_db import init
    await init()
    yield


app = FastAPI(
    title="CloudPG Control Plane",
    version="0.1.0",
    description="AI-Native Serverless PostgreSQL — Control Plane API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(projects.router, prefix="/api/v1")
app.include_router(databases.router, prefix="/api/v1")
app.include_router(computes.router, prefix="/api/v1")
app.include_router(endpoints.router, prefix="/api/v1")
app.include_router(backups.router, prefix="/api/v1")
app.include_router(metrics.router, prefix="/api/v1")
app.include_router(roles.router, prefix="/api/v1")


@app.get("/health", tags=["meta"])
async def health():
    return {"status": "ok", "service": "cloudpg-control-plane"}

"""Compute 路由 (Serverless Compute 启停/规格/挂起恢复)。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from apps.api.deps import get_db
from apps.api.security import AuthContext, require_auth
from db.session import AsyncSession
from services import compute as compute_svc

router = APIRouter(prefix="/computes", tags=["computes"])


class ComputeCreate(BaseModel):
    name: str
    cpu: float = 1.0


class ResizeRequest(BaseModel):
    cpu: float


class AutoSuspendRequest(BaseModel):
    auto_suspend: bool


@router.post("", response_model=dict)
async def create_compute(
    body: ComputeCreate, auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)
):
    try:
        comp = await compute_svc.create(db, organization_id=auth.organization_id, project_id=auth.project_id, name=body.name, cpu=body.cpu)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"id": comp.id, "name": comp.name, "cpu": comp.cpu, "memory_gb": comp.memory_gb, "status": comp.status}


@router.post("/{compute_id}/start", response_model=dict)
async def start(compute_id: str, auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    comp = await compute_svc.start_compute(db, compute_id=compute_id, organization_id=auth.organization_id, project_id=auth.project_id)
    return {"id": comp.id, "status": comp.status}


@router.post("/{compute_id}/stop", response_model=dict)
async def stop(compute_id: str, auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    comp = await compute_svc.stop_compute(db, compute_id=compute_id, organization_id=auth.organization_id, project_id=auth.project_id)
    return {"id": comp.id, "status": comp.status}


@router.post("/{compute_id}/restart", response_model=dict)
async def restart(compute_id: str, auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    comp = await compute_svc.restart_compute(db, compute_id=compute_id, organization_id=auth.organization_id, project_id=auth.project_id)
    return {"id": comp.id, "status": comp.status}


@router.post("/{compute_id}/suspend", response_model=dict)
async def suspend(compute_id: str, auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    comp = await compute_svc.suspend_compute(db, compute_id=compute_id, organization_id=auth.organization_id, project_id=auth.project_id)
    return {"id": comp.id, "status": comp.status}


@router.post("/{compute_id}/resume", response_model=dict)
async def resume(compute_id: str, auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    comp = await compute_svc.resume_compute(db, compute_id=compute_id, organization_id=auth.organization_id, project_id=auth.project_id)
    return {"id": comp.id, "status": comp.status}


@router.patch("/{compute_id}", response_model=dict)
async def resize(compute_id: str, body: ResizeRequest, auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    try:
        comp = await compute_svc.resize_compute(db, compute_id=compute_id, organization_id=auth.organization_id, project_id=auth.project_id, cpu=body.cpu)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"id": comp.id, "cpu": comp.cpu, "memory_gb": comp.memory_gb, "status": comp.status}


@router.patch("/{compute_id}/auto-suspend", response_model=dict)
async def set_auto_suspend(compute_id: str, body: AutoSuspendRequest, auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    comp = await compute_svc.set_auto_suspend(db, compute_id=compute_id, organization_id=auth.organization_id, project_id=auth.project_id, auto_suspend=body.auto_suspend)
    return {"id": comp.id, "auto_suspend": comp.auto_suspend}

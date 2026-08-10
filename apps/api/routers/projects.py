"""项目路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from apps.api.deps import get_db
from apps.api.security import AuthContext, require_auth
from db.session import AsyncSession
from services import project as project_svc

router = APIRouter()


class ProjectCreate(BaseModel):
    name: str
    region: str = "local"


@router.post("", response_model=dict)
async def create_project(
    body: ProjectCreate, auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)
):
    proj = await project_svc.create(db, organization_id=auth.organization_id, name=body.name, region=body.region)
    return {"id": proj.id, "name": proj.name, "region": proj.region}


@router.get("", response_model=list[dict])
async def list_projects(auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    items = await project_svc.list_by_org(db, auth.organization_id)
    return [{"id": p.id, "name": p.name, "region": p.region, "never_suspend": p.never_suspend} for p in items]


@router.get("/{project_id}", response_model=dict)
async def get_project(project_id: str, auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    proj = await project_svc.get(db, project_id)
    if not proj or proj.organization_id != auth.organization_id:
        return {"error": "not found"}
    return {"id": proj.id, "name": proj.name, "region": proj.region, "never_suspend": proj.never_suspend}


@router.patch("/{project_id}/never-suspend", response_model=dict)
async def set_never_suspend(
    project_id: str, value: bool = False, auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)
):
    proj = await project_svc.set_never_suspend(db, project_id, value)
    return {"id": proj.id, "never_suspend": proj.never_suspend} if proj else {"error": "not found"}

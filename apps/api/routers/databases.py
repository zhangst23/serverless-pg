"""数据库生命周期路由 (Create / Delete / Query)。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from apps.api.deps import get_db
from apps.api.security import AuthContext, require_auth
from db.session import AsyncSession
from services import database as db_svc
from services import compute as compute_svc
from managers.database_manager import list_tables, read_logfile, run_query

router = APIRouter(prefix="/databases", tags=["databases"])


class DatabaseCreate(BaseModel):
    name: str
    cpu: float = 1.0
    storage_gb: int = 10


class QueryRequest(BaseModel):
    sql: str


@router.post("", response_model=dict)
async def create_database(
    body: DatabaseCreate, auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)
):
    try:
        database = await db_svc.create(
            db, organization_id=auth.organization_id, project_id=auth.project_id, name=body.name, cpu=body.cpu, storage_gb=body.storage_gb
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"id": database.id, "name": database.name, "status": database.status, "compute_id": database.compute_id}


@router.get("", response_model=list[dict])
async def list_databases(auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    items = await db_svc.list_by_project(db, auth.project_id)
    return [
        {
            "id": d.id,
            "name": d.name,
            "status": d.status,
            "compute_id": d.compute_id,
            "storage_gb": d.compute.storage_gb if d.compute else None,
        }
        for d in items
    ]


@router.get("/{database_id}", response_model=dict)
async def get_database(database_id: str, auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    d = await db_svc.get(db, database_id)
    if not d:
        raise HTTPException(status_code=404, detail="not found")
    return {
        "id": d.id,
        "name": d.name,
        "status": d.status,
        "compute_id": d.compute_id,
        "storage_gb": d.compute.storage_gb if d.compute else None,
    }


@router.get("/{database_id}/tables", response_model=list[dict])
async def table_list(database_id: str, auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    d = await db_svc.get(db, database_id)
    if not d or not d.compute_id:
        raise HTTPException(status_code=404, detail="not found")
    if d.status == "suspended" and d.compute_id:
        await compute_svc.resume_compute(db, compute_id=d.compute_id, organization_id=auth.organization_id, project_id=auth.project_id)
    tables = list_tables(d.compute_id, d.name)
    return [{"name": t} for t in tables]


@router.get("/{database_id}/logs", response_model=dict)
async def logs(database_id: str, tail: int = 200, auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    d = await db_svc.get(db, database_id)
    if not d or not d.compute_id:
        raise HTTPException(status_code=404, detail="not found")
    content = read_logfile(d.compute_id, tail=tail)
    return {"database_id": database_id, "log": content}


@router.delete("/{database_id}", response_model=dict)
async def delete_database(database_id: str, auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    try:
        await db_svc.delete(db, database_id=database_id, organization_id=auth.organization_id, project_id=auth.project_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return {"deleted": database_id}


@router.post("/{database_id}/query", response_model=dict)
async def query_database(
    database_id: str, body: QueryRequest, auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)
):
    d = await db_svc.get(db, database_id)
    if not d or not d.compute_id:
        raise HTTPException(status_code=404, detail="not found")
    # 若已挂起，自动 Resume (Serverless 体验)
    if d.status == "suspended" and d.compute_id:
        await compute_svc.resume_compute(db, compute_id=d.compute_id, organization_id=auth.organization_id, project_id=auth.project_id)
        d.status = "active"
        await db.commit()
    try:
        rows = run_query(d.compute_id, d.name, body.sql)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"rows": rows}

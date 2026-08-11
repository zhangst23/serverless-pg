"""备份路由 (手动备份 / 恢复 / 列表)。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from apps.api.deps import get_db
from apps.api.security import AuthContext, require_auth
from db.session import AsyncSession
from services import backup as backup_svc
from services import database as db_svc

router = APIRouter(prefix="/backups", tags=["backups"])


class BackupRequest(BaseModel):
    database_id: str


@router.post("", response_model=dict)
async def create_backup(body: BackupRequest, auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    d = await db_svc.get(db, body.database_id)
    if not d or not d.compute_id:
        raise HTTPException(status_code=404, detail="database not found")
    bk = await backup_svc.create_backup(
        db, organization_id=auth.organization_id, project_id=auth.project_id,
        database_id=d.id, database_name=d.name, compute_id=d.compute_id, kind="manual",
    )
    return {"id": bk.id, "status": bk.status, "location": bk.location}


@router.post("/{backup_id}/restore", response_model=dict)
async def restore(backup_id: str, auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    # 通过 backup 反查 compute/database
    from sqlalchemy import select
    from db.models import Backup
    res = await db.execute(select(Backup).where(Backup.id == backup_id, Backup.organization_id == auth.organization_id))
    bk = res.scalar_one_or_none()
    if not bk:
        raise HTTPException(status_code=404, detail="backup not found")
    d = await db_svc.get(db, bk.database_id)
    if not d or not d.compute_id:
        raise HTTPException(status_code=404, detail="database not found")
    result = await backup_svc.restore(db, backup_id=backup_id, compute_id=d.compute_id, database_name=d.name)
    return {"id": result.id, "status": result.status}


@router.get("", response_model=list[dict])
async def list_backups(auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from db.models import Backup, Database
    res = await db.execute(
        select(Backup, Database.name)
        .join(Database, Backup.database_id == Database.id, isouter=True)
        .where(Backup.project_id == auth.project_id)
        .order_by(Backup.created_at.desc())
    )
    return [
        {
            "id": b.id,
            "database_id": b.database_id,
            "database_name": db_name or b.database_id,
            "kind": b.kind,
            "status": b.status,
            "created_at": b.created_at.isoformat() if b.created_at else None,
        }
        for b, db_name in res.all()
    ]

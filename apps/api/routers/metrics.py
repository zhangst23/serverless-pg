"""指标路由 (8 项监控)。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from apps.api.deps import get_db
from apps.api.security import AuthContext, require_auth
from db.session import AsyncSession
from services import database as db_svc
from services import metrics as metrics_svc

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/databases/{database_id}", response_model=dict)
async def metrics(database_id: str, auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    d = await db_svc.get(db, database_id)
    if not d or not d.compute_id:
        raise HTTPException(status_code=404, detail="not found")
    storage_limit = getattr(d, "storage_gb", None) or 10.0
    data = await metrics_svc.collect(d.compute_id, d.name, storage_limit_gb=float(storage_limit))
    return {"database_id": database_id, **data}

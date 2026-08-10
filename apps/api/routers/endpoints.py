"""Endpoint 路由 (连接串 / 连接池 / 限制)。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from apps.api.deps import get_db
from apps.api.security import AuthContext, require_auth
from db.session import AsyncSession
from services import endpoint as endpoint_svc

router = APIRouter(prefix="/endpoints", tags=["endpoints"])


@router.get("/{endpoint_id}", response_model=dict)
async def get_endpoint(endpoint_id: str, auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    ep = await endpoint_svc.get(db, endpoint_id)
    if not ep:
        raise HTTPException(status_code=404, detail="not found")
    return {
        "id": ep.id,
        "connection_string": ep.connection_string,
        "pool_mode": ep.pool_mode,
        "connection_limit": ep.connection_limit,
        "host": ep.host,
        "port": ep.port,
    }

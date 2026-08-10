"""Endpoint Service — 生成标准连接串 + 连接池配置。"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.config import settings
from db.models import Endpoint


def _build_connection_string(database_name: str, port: int) -> str:
    return (
        f"postgres://cloudpg:@{settings.external_host}:{settings.pgbouncer_port}/{database_name}"
    )


async def create(
    db: AsyncSession,
    *,
    organization_id: str,
    project_id: str,
    database_name: str,
    compute_port: int,
    pool_mode: str = "transaction",
    connection_limit: int = 100,
) -> Endpoint:
    ep = Endpoint(
        organization_id=organization_id,
        project_id=project_id,
        host=settings.external_host,
        port=settings.pgbouncer_port,
        pool_mode=pool_mode,
        connection_limit=connection_limit,
        connection_string=_build_connection_string(database_name, compute_port),
    )
    db.add(ep)
    await db.flush()
    await db.commit()
    await db.refresh(ep)
    return ep


async def get(db: AsyncSession, endpoint_id: str) -> Endpoint | None:
    from sqlalchemy import select
    res = await db.execute(select(Endpoint).where(Endpoint.id == endpoint_id))
    return res.scalar_one_or_none()

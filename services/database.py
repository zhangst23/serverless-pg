"""Database Service — Database Lifecycle (Create/Start/Stop/Restart/Delete)。"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Database
from managers.database_manager import create_database, drop_database
from services import compute as compute_svc
from services import endpoint as endpoint_svc


async def create(
    db: AsyncSession,
    *,
    organization_id: str,
    project_id: str,
    name: str,
    cpu: float = 1.0,
    storage_gb: int = 10,
) -> Database:
    # 1) 分配 Compute (存储档位挂到计算实例的磁盘)
    comp = await compute_svc.create(
        db,
        organization_id=organization_id,
        project_id=project_id,
        name=f"{name}-compute",
        cpu=cpu,
        storage_gb=storage_gb,
    )
    # 2) 生成 Endpoint
    ep = await endpoint_svc.create(
        db, organization_id=organization_id, project_id=project_id, database_name=name, compute_port=comp.port
    )
    # 3) 建库
    database = Database(
        organization_id=organization_id,
        project_id=project_id,
        name=name,
        status="creating",
        compute_id=comp.id,
        endpoint_id=ep.id,
    )
    db.add(database)
    await db.flush()
    create_database(comp.id, name)
    database.status = "active"
    await db.commit()
    await db.refresh(database)
    return database


async def delete(db: AsyncSession, *, database_id: str, organization_id: str, project_id: str) -> None:
    from sqlalchemy import select
    res = await db.execute(
        select(Database).where(
            Database.id == database_id,
            Database.organization_id == organization_id,
            Database.project_id == project_id,
        )
    )
    database = res.scalar_one_or_none()
    if not database:
        raise LookupError("database not found")
    if database.compute_id:
        drop_database(database.compute_id, database.name)
        await compute_svc.stop_compute(
            db, compute_id=database.compute_id, organization_id=organization_id, project_id=project_id
        )
    await db.delete(database)
    await db.commit()


async def get(db: AsyncSession, database_id: str) -> Database | None:
    from sqlalchemy import select
    res = await db.execute(select(Database).where(Database.id == database_id))
    return res.scalar_one_or_none()


async def list_by_project(db: AsyncSession, project_id: str) -> list[Database]:
    from sqlalchemy import select
    res = await db.execute(select(Database).where(Database.project_id == project_id))
    return list(res.scalars().all())

"""Project Service — 项目增删改查 (多租户隔离)。"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Project


async def create(db: AsyncSession, *, organization_id: str, name: str, region: str = "local") -> Project:
    proj = Project(organization_id=organization_id, project_id="", name=name, region=region)
    # project_id 与自身 id 一致，方便隔离查询
    db.add(proj)
    await db.flush()
    proj.project_id = proj.id
    await db.commit()
    await db.refresh(proj)
    return proj


async def list_by_org(db: AsyncSession, organization_id: str) -> list[Project]:
    from sqlalchemy import select
    res = await db.execute(select(Project).where(Project.organization_id == organization_id))
    return list(res.scalars().all())


async def get(db: AsyncSession, project_id: str) -> Project | None:
    from sqlalchemy import select
    res = await db.execute(select(Project).where(Project.id == project_id))
    return res.scalar_one_or_none()


async def set_never_suspend(db: AsyncSession, project_id: str, value: bool) -> Project | None:
    proj = await get(db, project_id)
    if proj:
        proj.never_suspend = value
        await db.commit()
        await db.refresh(proj)
    return proj

"""Project Service — 项目增删改查 (多租户隔离)。"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Project


async def create(db: AsyncSession, *, organization_id: str, name: str, region: str = "local") -> Project:
    # 项目对外标识即 name (slug): 资源 project_id 与 API Key 的 proj_<name> 段均以此为隔离键
    slug = name.strip()
    if not slug:
        raise ValueError("name 不能为空")
    proj = Project(id=slug, organization_id=organization_id, project_id=slug, name=name, region=region)
    db.add(proj)
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

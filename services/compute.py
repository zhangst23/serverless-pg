"""Compute Service — Serverless Compute 生命周期与规格。"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Compute, Database
from managers.compute_manager import (
    gen_password,
    is_running,
    provision,
    resize,
    restart,
    start,
    stop,
    suspend,
    resume,
)

CPU_MEM = {0.25: 0.5, 0.5: 1.0, 1.0: 2.0, 2.0: 4.0, 4.0: 8.0}


async def create(db: AsyncSession, *, organization_id: str, project_id: str, name: str, cpu: float) -> Compute:
    if cpu not in CPU_MEM:
        raise ValueError(f"非法 CPU 档位 {cpu}")
    memory_gb = CPU_MEM[cpu]
    comp = Compute(
        organization_id=organization_id,
        project_id=project_id,
        name=name,
        cpu=cpu,
        memory_gb=memory_gb,
        status="provisioning",
    )
    db.add(comp)
    await db.flush()

    info = provision(comp.id, cpu, memory_gb)
    comp.port = info["port"]
    comp.data_dir = info["data_dir"]
    comp.status = "running" if is_running(comp.id) else "error"
    await db.commit()
    await db.refresh(comp)
    return comp


async def _get_checked(db: AsyncSession, compute_id: str, organization_id: str, project_id: str) -> Compute:
    from sqlalchemy import select
    res = await db.execute(
        select(Compute).where(
            Compute.id == compute_id,
            Compute.organization_id == organization_id,
            Compute.project_id == project_id,
        )
    )
    comp = res.scalar_one_or_none()
    if not comp:
        raise LookupError("compute not found")
    return comp


async def start_compute(db: AsyncSession, *, compute_id: str, organization_id: str, project_id: str) -> Compute:
    comp = await _get_checked(db, compute_id, organization_id, project_id)
    start(comp.id)
    comp.status = "running" if is_running(comp.id) else "error"
    await db.commit()
    await db.refresh(comp)
    return comp


async def stop_compute(db: AsyncSession, *, compute_id: str, organization_id: str, project_id: str) -> Compute:
    comp = await _get_checked(db, compute_id, organization_id, project_id)
    stop(comp.id)
    comp.status = "suspended"
    await db.commit()
    await db.refresh(comp)
    return comp


async def restart_compute(db: AsyncSession, *, compute_id: str, organization_id: str, project_id: str) -> Compute:
    comp = await _get_checked(db, compute_id, organization_id, project_id)
    restart(comp.id)
    comp.status = "running" if is_running(comp.id) else "error"
    await db.commit()
    await db.refresh(comp)
    return comp


async def suspend_compute(db: AsyncSession, *, compute_id: str, organization_id: str, project_id: str) -> Compute:
    comp = await _get_checked(db, compute_id, organization_id, project_id)
    suspend(comp.id)
    comp.status = "suspended"
    await db.commit()
    await db.refresh(comp)
    return comp


async def resume_compute(db: AsyncSession, *, compute_id: str, organization_id: str, project_id: str) -> Compute:
    comp = await _get_checked(db, compute_id, organization_id, project_id)
    resume(comp.id)
    comp.status = "running" if is_running(comp.id) else "error"
    await db.commit()
    await db.refresh(comp)
    return comp


async def resize_compute(db: AsyncSession, *, compute_id: str, organization_id: str, project_id: str, cpu: float) -> Compute:
    comp = await _get_checked(db, compute_id, organization_id, project_id)
    if cpu not in CPU_MEM:
        raise ValueError(f"非法 CPU 档位 {cpu}")
    memory_gb = CPU_MEM[cpu]
    resize(comp.id, cpu, memory_gb)
    comp.cpu = cpu
    comp.memory_gb = memory_gb
    comp.status = "running" if is_running(comp.id) else "error"
    await db.commit()
    await db.refresh(comp)
    return comp

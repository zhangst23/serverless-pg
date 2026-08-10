"""Backup Service — 手动/自动备份、恢复、PITR (MVP: pg_dump/pg_restore 到本地归档)。"""
from __future__ import annotations

import os
import subprocess

from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.config import settings
from db.models import Backup
from managers.compute_manager import _port_for, _run


async def create_backup(
    db: AsyncSession, *, organization_id: str, project_id: str, database_id: str, database_name: str, compute_id: str, kind: str = "manual"
) -> Backup:
    archive_dir = os.path.join(settings.data_root, compute_id, "backups")
    os.makedirs(archive_dir, exist_ok=True)
    _run("root", ["chown", "-R", "postgres:postgres", archive_dir])
    location = os.path.join(archive_dir, f"{database_name}_{kind}.dump")

    pg_bin = settings.pg_bin
    port = _port_for(compute_id)
    r = _run("postgres", [f"{pg_bin}/pg_dump", "-h", "localhost", "-p", str(port), "-U", "cloudpg", "-F", "c", "-f", location, database_name])
    status = "completed" if r.returncode == 0 else "failed"

    bk = Backup(
        organization_id=organization_id,
        project_id=project_id,
        database_id=database_id,
        kind=kind,
        status=status,
        location=location,
    )
    db.add(bk)
    await db.commit()
    await db.refresh(bk)
    return bk


async def restore(db: AsyncSession, *, backup_id: str, compute_id: str, database_name: str) -> Backup:
    from sqlalchemy import select
    res = await db.execute(select(Backup).where(Backup.id == backup_id))
    bk = res.scalar_one_or_none()
    if not bk or not bk.location:
        raise LookupError("backup not found")
    pg_bin = settings.pg_bin
    port = _port_for(compute_id)
    r = _run("postgres", [f"{pg_bin}/pg_restore", "-h", "localhost", "-p", str(port), "-U", "cloudpg", "-d", database_name, "-c", bk.location])
    bk.status = "completed" if r.returncode == 0 else "failed"
    await db.commit()
    await db.refresh(bk)
    return bk


async def list_by_project(db: AsyncSession, project_id: str) -> list[Backup]:
    from sqlalchemy import select
    res = await db.execute(select(Backup).where(Backup.project_id == project_id))
    return list(res.scalars().all())

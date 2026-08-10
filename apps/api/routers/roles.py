"""角色与凭证路由 (DX): 创建角色 / 重置密码 / 生成多语言连接串。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from apps.api.config import settings
from apps.api.deps import get_db
from apps.api.security import AuthContext, require_auth
from db.models import Role
from db.session import AsyncSession
from managers.compute_manager import gen_password
from managers.database_manager import create_role
from services import database as db_svc

router = APIRouter(tags=["roles"])


class RoleCreate(BaseModel):
    name: str
    privilege: str = "readwrite"  # readwrite / readonly


def _conn_string(database_name: str, user: str, password: str) -> str:
    return f"postgres://{user}:{password}@{settings.external_host}:{settings.pgbouncer_port}/{database_name}"


def _snippets(database_name: str, user: str, password: str) -> dict:
    cs = _conn_string(database_name, user, password)
    return {
        "connection_string": cs,
        "env": f"DATABASE_URL={cs}",
        "node": f'const {{ Pool }} = require("pg");\nconst pool = new Pool({{ connectionString: "{cs}" }});',
        "python": f'import psycopg\nconn = psycopg.connect("{cs}")',
        "go": f'connStr := "{cs}"',
        "rust": f'let url = "{cs}";',
    }


@router.post("/projects/{project_id}/roles", response_model=dict)
async def create_role_endpoint(
    project_id: str, body: RoleCreate, auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)
):
    if body.privilege not in ("readwrite", "readonly"):
        raise HTTPException(status_code=400, detail="privilege must be readwrite/readonly")
    # 找到该项目下某 database 的 compute 以创建实际 PG 角色
    dbs = await db_svc.list_by_project(db, project_id)
    if not dbs or not dbs[0].compute_id:
        raise HTTPException(status_code=400, detail="no database/compute available")
    password = gen_password()
    create_role(dbs[0].compute_id, body.name, password, readonly=(body.privilege == "readonly"))
    role = Role(
        organization_id=auth.organization_id, project_id=project_id,
        name=body.name, privilege=body.privilege, password=password,
    )
    db.add(role)
    await db.flush()
    await db.commit()
    await db.refresh(role)
    return {
        "id": role.id, "name": role.name, "privilege": role.privilege,
        "snippets": _snippets(dbs[0].name, body.name, password),
    }


@router.post("/projects/{project_id}/roles/{role_id}/reset-password", response_model=dict)
async def reset_password(project_id: str, role_id: str, auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    res = await db.execute(select(Role).where(Role.id == role_id, Role.project_id == project_id))
    role = res.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="role not found")
    dbs = await db_svc.list_by_project(db, project_id)
    new_pw = gen_password()
    if dbs and dbs[0].compute_id:
        create_role(dbs[0].compute_id, role.name, new_pw, readonly=(role.privilege == "readonly"))
    role.password = new_pw
    await db.commit()
    return {"id": role.id, "snippets": _snippets(dbs[0].name if dbs else "", role.name, new_pw)}


@router.delete("/projects/{project_id}/roles/{role_id}", response_model=dict)
async def delete_role(project_id: str, role_id: str, auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    res = await db.execute(select(Role).where(Role.id == role_id, Role.project_id == project_id))
    role = res.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="role not found")
    await db.delete(role)
    await db.commit()
    return {"deleted": role_id}


@router.get("/projects/{project_id}/connection-string", response_model=dict)
async def connection_string(project_id: str, auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    dbs = await db_svc.list_by_project(db, project_id)
    if not dbs:
        raise HTTPException(status_code=404, detail="no database")
    cs = _conn_string(dbs[0].name, "cloudpg", "")
    return {"connection_string": cs, "snippets": _snippets(dbs[0].name, "cloudpg", "")}

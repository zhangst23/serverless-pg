"""认证路由: User 通道账密登录 / 当前用户 / 登出。

登录流程:
  1. 客户端 POST /api/v1/auth/login {email, password}
  2. 服务端校验 users 表 (bcrypt hashed_password)
  3. 解析该用户所属组织 (members -> organization)；默认取首个成员关系
  4. 签发 Session JWT (actor=user)，返回 {access_token, token_type, user}
  5. Web 前端将该 JWT 存于 httpOnly cookie，后续请求带 Authorization: Bearer
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.deps import get_db
from apps.api.security import AuthContext, create_session_token, require_auth
from db.models import Member, Organization, Project, User

try:
    import bcrypt

    _HAS_BCRYPT = True
except Exception:  # pragma: no cover
    _HAS_BCRYPT = False


def hash_password(plain: str) -> str:
    if not _HAS_BCRYPT:
        raise RuntimeError("bcrypt unavailable")
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    if not _HAS_BCRYPT:
        return False
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except (ValueError, TypeError):
        return False


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class CurrentUserResponse(BaseModel):
    user_id: str
    email: str
    organization_id: str
    project_id: str | None
    actor: str


router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    if not _HAS_BCRYPT:
        raise HTTPException(status_code=500, detail="password backend unavailable")

    res = await db.execute(select(User).where(User.email == body.email.strip().lower()))
    user = res.scalar_one_or_none()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="invalid email or password")

    # 解析组织上下文 (默认取首个成员关系)
    mres = await db.execute(
        select(Member).where(Member.user_id == user.id).order_by(Member.created_at)
    )
    member = mres.scalars().first()
    organization_id = member.organization_id if member else None
    if not organization_id:
        raise HTTPException(status_code=403, detail="user has no organization")

    # 默认项目: 取该组织下首个项目
    pres = await db.execute(
        select(Project)
        .where(Project.organization_id == organization_id)
        .order_by(Project.created_at)
    )
    project = pres.scalars().first()
    project_id = project.id if project else None

    token = create_session_token(
        user_id=user.id,
        organization_id=organization_id,
        project_id=project_id,
    )
    return LoginResponse(
        access_token=token,
        user={
            "id": user.id,
            "email": user.email,
            "organization_id": organization_id,
        },
    )


@router.get("/me", response_model=CurrentUserResponse)
async def me(ctx: AuthContext = Depends(require_auth)):
    return CurrentUserResponse(
        user_id=ctx.user_id or "",
        email="",
        organization_id=ctx.organization_id,
        project_id=ctx.project_id,
        actor=ctx.actor,
    )


@router.post("/logout")
async def logout():
    # 无状态 JWT: 服务端无需撤销，前端删除 cookie 即可。
    return {"ok": True}

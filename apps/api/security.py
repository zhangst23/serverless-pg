"""鉴权: Agent (X-API-Key) 与 User (Session JWT) 双通道。

- Agent 通道:  CLI / SDK 使用 X-API-Key (key 形如 org_<org>__proj_<proj>__<rand>)，actor="agent"。
- User 通道:    Web 控制台账密登录后，由本服务签发 Session JWT (HMAC-SHA256)，
                actor="user"。浏览器直连 FastAPI 时通过 Authorization: Bearer <jwt> 传递。

信任边界: 两种凭证都经本服务验签/解析，JWT 的 user/org/project 上下文只来自本服务签名，
FastAPI 绝不信任前端声称的租户信息。
"""
from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timedelta, timezone

from jose import jwt
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from apps.api.config import settings

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
BEARER = HTTPBearer(auto_error=False)

# Session JWT 默认有效期
SESSION_TTL = timedelta(days=1)


def hash_api_key(key: str) -> str:
    return hmac.new(
        settings.api_key_secret.encode(), key.encode(), hashlib.sha256
    ).hexdigest()


def create_token(organization_id: str, project_id: str) -> str:
    """Agent 通道令牌 (保留现有约定，非必用)。"""
    payload = {
        "organization_id": organization_id,
        "project_id": project_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=30),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="invalid token") from exc


def create_session_token(
    *, user_id: str, organization_id: str, project_id: str | None = None
) -> str:
    """签发 User 通道 Session JWT。"""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "organization_id": organization_id,
        "project_id": project_id,
        "typ": "user",
        "iat": now,
        "exp": now + SESSION_TTL,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


class AuthContext(BaseModel):
    actor: str  # "user" | "agent"
    user_id: str | None = None
    organization_id: str
    project_id: str | None = None


def _parse_api_key(api_key: str) -> AuthContext:
    """Agent 通道: 约定格式 org_<org>__proj_<proj>__<random>。"""
    try:
        org_part, proj_part, _rand = api_key.split("__")
        organization_id = org_part.replace("org_", "")
        project_id = proj_part.replace("proj_", "")
        if not organization_id or not project_id:
            raise ValueError("empty org/project")
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="malformed API key") from exc
    return AuthContext(
        actor="agent",
        organization_id=organization_id,
        project_id=project_id,
    )


def _parse_bearer(creds: HTTPAuthorizationCredentials) -> AuthContext:
    """User 通道: 校验本服务签发的 Session JWT。"""
    payload = decode_token(creds.credentials)
    if payload.get("typ") != "user":
        raise HTTPException(status_code=401, detail="invalid token type")
    user_id = payload.get("sub")
    organization_id = payload.get("organization_id")
    project_id = payload.get("project_id")
    if not user_id or not organization_id:
        raise HTTPException(status_code=401, detail="invalid token claims")
    return AuthContext(
        actor="user",
        user_id=user_id,
        organization_id=organization_id,
        project_id=project_id,
    )


async def require_auth(
    api_key: str | None = Security(API_KEY_HEADER),
    creds: HTTPAuthorizationCredentials | None = Security(BEARER),
) -> AuthContext:
    """双通道鉴权:

    - 命中 X-API-Key  → Agent 通道
    - 命中 Bearer     → User 通道
    两者皆无则 401。
    """
    if creds and creds.credentials:
        return _parse_bearer(creds)
    if api_key:
        return _parse_api_key(api_key)
    raise HTTPException(status_code=401, detail="missing credentials")

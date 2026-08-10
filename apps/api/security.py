"""轻量鉴权: API Key / JWT (MVP 自研方案)。"""
from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timedelta, timezone

from jose import jwt
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from apps.api.config import settings

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def hash_api_key(key: str) -> str:
    return hmac.new(
        settings.api_key_secret.encode(), key.encode(), hashlib.sha256
    ).hexdigest()


def create_token(organization_id: str, project_id: str) -> str:
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


class AuthContext(BaseModel):
    organization_id: str
    project_id: str


async def require_auth(
    api_key: str | None = Security(API_KEY_HEADER),
) -> AuthContext:
    """MVP: 通过 X-API-Key 解析组织/项目上下文。

    真实环境应查询 api_keys 表校验 key_hash。这里用约定前缀简化:
      key 形如  org_<org>__proj_<proj>__<random>
    """
    if not api_key:
        raise HTTPException(status_code=401, detail="missing API key")
    try:
        _, org, _p, proj, _rand = api_key.split("__")
        organization_id = org.replace("org_", "")
        project_id = proj.replace("proj_", "")
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="malformed API key") from exc
    return AuthContext(organization_id=organization_id, project_id=project_id)

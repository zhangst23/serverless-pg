"""创建初始管理员用户 + 组织，并生成一个 Agent API Key。

用法:
  python -m db.seed_admin \
      --email admin@example.com --password 'StrongPass123' \
      --org 'acme' --org-name 'Acme Inc'

会在 organizations / users / members / api_keys 写入记录，并打印可用于
CLI/SDK 的 X-API-Key (格式 org_<org>__proj_<proj>__<rand>)。
"""
from __future__ import annotations

import argparse
import asyncio
import os
import secrets

from sqlalchemy import select

from apps.api.config import settings
from apps.api.security import hash_api_key
from db.base import gen_id
from db.models import ApiKey, Member, Organization, User
from db.session import AsyncSessionLocal

try:
    from passlib.context import CryptContext

    _pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
except Exception:  # pragma: no cover
    _pwd = None


def make_api_key(org: str, proj: str) -> str:
    return f"org_{org}__proj_{proj}__{secrets.token_hex(6)}"


async def seed(email: str, password: str, org_slug: str, org_name: str) -> None:
    email = email.strip().lower()
    async with AsyncSessionLocal() as db:
        existing = await db.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none():
            print(f"[skip] user {email} already exists")
            return

        org = Organization(id=gen_id("org"), name=org_name, slug=org_slug)
        db.add(org)
        await db.flush()

        # 默认项目 (agent 通道需要 project)
        from db.models import Project

        project = Project(id=gen_id("proj"), name="default", region="local")
        project.organization_id = org.id
        db.add(project)
        await db.flush()

        hashed = _pwd.hash(password) if _pwd else password
        user = User(id=gen_id("usr"), email=email, hashed_password=hashed)
        db.add(user)
        await db.flush()

        db.add(Member(organization_id=org.id, user_id=user.id, role="owner"))
        await db.flush()

        # Agent API Key
        raw = make_api_key(org_slug, project.id)
        db.add(ApiKey(name="default-agent", key_hash=hash_api_key(raw)))
        await db.commit()

        print("[ok] created:")
        print(f"  user : {email}")
        print(f"  org  : {org.id} (slug={org_slug})")
        print(f"  X-API-Key (agent): {raw}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--email", default=os.getenv("SEED_ADMIN_EMAIL", "admin@example.com"))
    ap.add_argument("--password", default=os.getenv("SEED_ADMIN_PASSWORD", "admin123456"))
    ap.add_argument("--org", default=os.getenv("SEED_ORG", "acme"))
    ap.add_argument("--org-name", default=os.getenv("SEED_ORG_NAME", "Acme Inc"))
    args = ap.parse_args()
    asyncio.run(seed(args.email, args.password, args.org, args.org_name))


if __name__ == "__main__":
    main()

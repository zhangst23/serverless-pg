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
    import bcrypt

    _HAS_BCRYPT = True
except Exception:  # pragma: no cover
    _HAS_BCRYPT = False


def make_api_key(org: str, proj: str) -> str:
    return f"org_{org}__proj_{proj}__{secrets.token_hex(6)}"


async def seed(
    email: str,
    password: str,
    org_slug: str,
    org_name: str,
    project_name: str = "demo",
) -> None:
    email = email.strip().lower()
    async with AsyncSessionLocal() as db:
        existing = await db.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none():
            print(f"[skip] user {email} already exists")
            return

        from db.models import Project

        # 复用已有组织 (按 slug)，不存在才新建
        org_row = (
            await db.execute(select(Organization).where(Organization.slug == org_slug))
        ).scalar_one_or_none()
        if org_row:
            org = org_row
            print(f"[reuse] org {org.id} (slug={org_slug})")
        else:
            org = Organization(id=gen_id("org"), name=org_name, slug=org_slug)
            db.add(org)
            await db.flush()

        # 复用已有项目: 优先按 project_id 字段 (demo 数据用字面量 "demo")，
        # 其次按 name，都不存在才新建；该项目作为登录默认 project。
        proj_row = (
            await db.execute(select(Project).where(Project.project_id == project_name))
        ).scalar_one_or_none()
        if not proj_row:
            proj_row = (
                await db.execute(select(Project).where(Project.name == project_name))
            ).scalar_one_or_none()
        if proj_row:
            project = proj_row
            print(f"[reuse] project {project.id} (name={project_name})")
        else:
            project = Project(id=gen_id("proj"), name=project_name, region="local")
            project.organization_id = org.id
            project.project_id = project.id  # 自引用租户隔离
            db.add(project)
            await db.flush()

        if not _HAS_BCRYPT:
            raise RuntimeError("bcrypt unavailable")
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        user = User(id=gen_id("usr"), email=email, hashed_password=hashed)
        db.add(user)
        await db.flush()

        db.add(Member(organization_id=org.id, user_id=user.id, role="owner"))
        await db.flush()

        # Agent API Key (使用 project.id 作为 proj 段，与 demo 数据对齐)
        raw = make_api_key(org_slug, project.id)
        api_key = ApiKey(name="default-agent", key_hash=hash_api_key(raw))
        api_key.organization_id = org.id
        api_key.project_id = project.id
        db.add(api_key)
        await db.commit()

        print("[ok] created:")
        print(f"  user : {email}")
        print(f"  org  : {org.id} (slug={org_slug})")
        print(f"  project (default): {project.id} (name={project_name})")
        print(f"  X-API-Key (agent): {raw}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--email", default=os.getenv("SEED_ADMIN_EMAIL", "admin@example.com"))
    ap.add_argument("--password", default=os.getenv("SEED_ADMIN_PASSWORD", "admin123456"))
    ap.add_argument("--org", default=os.getenv("SEED_ORG", "acme"))
    ap.add_argument("--org-name", default=os.getenv("SEED_ORG_NAME", "Acme Inc"))
    ap.add_argument("--project", default=os.getenv("SEED_PROJECT", "demo"))
    args = ap.parse_args()
    asyncio.run(seed(args.email, args.password, args.org, args.org_name, args.project))


if __name__ == "__main__":
    main()

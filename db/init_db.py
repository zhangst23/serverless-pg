"""初始化 Control Plane 数据库表 (MVP 用 create_all; 生产用 alembic)。

用法: python -m db.init_db
"""
from __future__ import annotations

import asyncio

from db.base import Base
from db.session import engine
import db.models  # noqa: F401 注册模型


async def init() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print("Control Plane 数据库表已创建/更新。")


if __name__ == "__main__":
    asyncio.run(init())

# CloudPG

AI-Native Serverless PostgreSQL 云数据库平台（第一版 / MVP）。

- **部署方式**：本地裸 VPS（不使用 Kubernetes），用 systemd / 进程管理拉起 PostgreSQL 实例。
- **Control Plane**：FastAPI + SQLAlchemy(async) + asyncpg，与用户 PostgreSQL 完全分离。
- **核心能力（Phase 1）**：Database Lifecycle / Serverless Compute / Storage / Connection / Backup / Monitoring。

## 目录结构

```text
apps/
  api/      FastAPI Control Plane
  cli/      cloudpg CLI
db/         models / session / alembic
managers/   database_manager / compute_manager / storage_manager
services/   服务层
deploy/     systemd 模板与脚本
packages/   sdk-python
dev/        docker-compose 本地对齐
```

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. Phase 0: 初始化底座（control plane PG + 验证脚本）
bash deploy/scripts/setup_base.sh

# 3. 初始化 Control Plane 数据库
alembic upgrade head

# 4. 启动 API
uvicorn apps.api.main:app --reload --port 8000
```

详见 `docs/PRD.md` 与 `docs/TODO.md`。

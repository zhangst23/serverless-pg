# CloudPG

AI-Native Serverless PostgreSQL 云数据库平台（第一版 / MVP）。

- **部署方式**：本地裸 VPS（不使用 Kubernetes），用 systemd / 进程管理拉起 PostgreSQL 实例。
- **Control Plane**：FastAPI + SQLAlchemy(async) + asyncpg，与用户 PostgreSQL 完全分离。
- **核心能力（Phase 1）**：Database Lifecycle / Serverless Compute / Storage / Connection / Backup / Monitoring。
- **管理面**：提供 Web 管理后台（Next.js）、CLI、Python SDK 三种入口。

## 架构

```text
User
  └─ Next.js Web 控制台 (apps/web :4000)
       └─ FastAPI Control Plane (apps/api :8000)
            ├─ Database / Compute / Storage Manager  (managers/)
            └─ Control Plane PostgreSQL (独立实例, 端口 5433)
                 └─ 用户 PostgreSQL 实例 (PG-01/02/03, 每库一实例)
                      └─ PgBouncer / 连接池
```

## 目录结构

```text
apps/
  api/      FastAPI Control Plane
  cli/      cloudpg CLI
  web/      Next.js 管理后台 (Web UI)
db/         models / session / init_db
managers/   database_manager / compute_manager / storage_manager
services/   服务层 (project/compute/database/endpoint/backup/metrics)
deploy/     systemd 模板与脚本
packages/   sdk-python
dev/        docker-compose 本地对齐
docs/       PRD.md / TODO.md / VERIFY.md
```

## 技术栈

| 层 | 技术 |
| --- | --- |
| Control Plane API | FastAPI + SQLAlchemy(async) + asyncpg + python-jose |
| 数据库管理 | PostgreSQL 18 (`pg_ctl` / `initdb` / `pg_dump`) |
| Web 管理后台 | Next.js 16 + TypeScript + Tailwind CSS v4 |
| CLI / SDK | Python (`cloudpg` CLI, `cloudpg` Python SDK) |
| 鉴权 | 双通道：User（账密登录 → Session JWT，直连 FastAPI）/ Agent（X-API-Key，CLI/SDK） |

## 快速开始

### 1. 后端（Control Plane）

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# Phase 0: 初始化底座 (control plane PG + systemd 模板)
bash deploy/scripts/setup_base.sh
# 创建 control plane 数据库 (setup_base 只初始化数据目录)
psql "postgresql://cloudpg@localhost:5433/postgres" -c "CREATE DATABASE cloudpg_cp OWNER cloudpg;"

# 初始化 Control Plane 表
python -m db.init_db

# 创建初始管理员用户 + 组织 + 生成 Agent API Key
python -m db.seed_admin --email admin@example.com --password 'StrongPass123' --org acme --org-name 'Acme Inc'

# 启动 API (默认 :8000)
uvicorn apps.api.main:app --port 8000
```

### 鉴权：两种通道

| 通道 | 身份 | 凭证 | 用途 |
| --- | --- | --- | --- |
| **User** | 人（Web 控制台） | 账密登录 → `Authorization: Bearer <Session JWT>` | 浏览器直连 FastAPI |
| **Agent** | 机器（CLI / SDK） | `X-API-Key` | 程序调用，格式 `org_<org>__proj_<proj>__<rand>` |

信任边界：
- 账密只在 FastAPI 校验（bcrypt），登录成功后由 FastAPI 用共享 `JWT_SECRET` 签发 Session JWT（HMAC-SHA256，1 天过期）。
- 浏览器直连 FastAPI（跨域），Session JWT 存前端 `localStorage`，每次请求带 `Authorization: Bearer`。
- Agent 通道（`X-API-Key`）完全独立保留，CLI/SDK 不变。
- 两种凭证都在 `require_auth` 验签/解析；FastAPI 不信任前端声称的 org/project，只认签名里的声明。

配置（`.env`，Next.js 与 FastAPI 均需）：`JWT_SECRET`、`JWT_ALGORITHM`（默认 HS256）、`API_KEY_SECRET`。

OpenAPI 文档：`http://localhost:8000/docs`

### 2. Web 管理后台（Next.js）

```bash
cd apps/web

# 开发模式
npm install
npm run dev              # http://localhost:3000

# 生产模式
npm run build
npm run start -p 4000    # 注意: 3000 常被系统服务占用, 建议用 4000
```

前端默认连接 `http://localhost:8000`，可用环境变量覆盖：

```bash
NEXT_PUBLIC_API_BASE=http://your-host:8000 npm run dev
```

**Web 控制台功能**：

| 页面 | 能力 |
| --- | --- |
| 登录 | 账密登录（User 通道，签发 Session JWT） |
| 概览 | 项目 / 数据库 / 备份统计 |
| 数据库 | 创建 / 删除 / SQL 控制台（自动 resume） |
| 计算实例 | 启停 / 挂起 / 恢复 / 调规格 (0.5~4 CPU) |
| 连接 & 角色 | 连接串 / 多语言片段 / 角色管理 |
| 备份 | 手动备份 / 恢复 |
| 监控 | 8 项核心指标 + 自动刷新 |


### 管理后台访问

http://<你的VPS公网IP>:3002/login

Web 控制台使用 **账密登录**（User 通道）。CLI / SDK 仍使用 **X-API-Key**（Agent 通道）。



### 3. CLI

```bash
python apps/cli/cloudpg.py --help
# login / projects / db / compute / logs / warm / sql / connect / dump / restore
```

### 4. Python SDK

```python
from cloudpg import Client
client = Client(api_key="org_x__proj_y__rand", base_url="http://localhost:8000")
print(client.list_databases())
```

## REST API 速览

| 资源 | 主要端点 |
| --- | --- |
| 项目 | `GET/POST /api/v1/projects`、`GET /api/v1/projects/{id}/connection-string` |
| 数据库 | `GET/POST /api/v1/databases`、`DELETE /api/v1/databases/{id}`、`POST /api/v1/databases/{id}/query` |
| 计算 | `POST /api/v1/computes/{id}/{start\|stop\|suspend\|resume\|restart}`、`PATCH /api/v1/computes/{id}` |
| 角色 | `GET/POST /api/v1/projects/{id}/roles`、`POST /api/v1/projects/{id}/roles/{rid}/reset-password`、`DELETE ...` |
| 备份 | `GET/POST /api/v1/backups`、`POST /api/v1/backups/{id}/restore` |
| 监控 | `GET /api/v1/metrics/databases/{id}` |

详见 `docs/PRD.md`、`docs/TODO.md` 与 `docs/VERIFY.md`（真实端到端验证手册）。

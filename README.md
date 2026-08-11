# CloudPG

AI-Native Serverless PostgreSQL 云数据库平台（第一版 / MVP）。

- **部署方式**：本地裸 VPS（不使用 Kubernetes），用 systemd / 进程管理拉起 PostgreSQL 实例。
- **Control Plane**：FastAPI + SQLAlchemy(async) + asyncpg，与用户 PostgreSQL 完全分离。
- **核心能力（Phase 1）**：Database Lifecycle / Serverless Compute / Storage / Connection / Backup / Monitoring / **PG Performance（扩展与参数调优）**。
- **管理面**：提供 Web 管理后台（Next.js）、CLI、Python SDK 三种入口。

## 架构

```text
User (浏览器)
  └─ Next.js Web 控制台 (apps/web, 生产 :3002 / 开发 :3000)
       └─ [账密登录] POST /api/v1/auth/login → 拿到 Session JWT
       └─ 后续请求带 Authorization: Bearer <JWT> (同源经 Nginx 反代 /api/)
  └─ CLI / SDK (Agent 通道) 直接带 X-API-Key 调用 :8000

FastAPI Control Plane (apps/api :8000)
  ├─ 鉴权双通道: require_auth → Bearer JWT (user) | X-API-Key (agent)
  ├─ Database / Compute / Storage Manager  (managers/)
  └─ Control Plane PostgreSQL (独立实例, 端口 5433)
       └─ 用户 PostgreSQL 实例 (PG-01/02/03, 每库一实例)
            └─ PgBouncer / 连接池
```

> 信任链：Web 控制台不持有密钥，账密只在 FastAPI 校验（bcrypt），登录后由
> FastAPI 用共享 `JWT_SECRET` 签发 Session JWT（HMAC-SHA256）。浏览器直连后端
> 时携带该 JWT；FastAPI 验签后只认 JWT 内的 `organization_id`/`project_id` 声明，
> 绝不信任前端声称的租户信息。

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
访问 http://217.69.2.217/login 即可用账密 admin@cloudpg.local / CloudPG@2026 登录。

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
npm install

# 开发模式
npm run dev              # http://localhost:3000

# 生产模式 (构建后用 Nginx 反代到 :3002)
npm run build
npx next start -p 3002
```

前端通过 `NEXT_PUBLIC_API_BASE` 决定后端地址：
- 留空（默认）→ 走**同源相对路径** `/api/...`，由 Nginx 把 `/api/` 反代到
  `127.0.0.1:8000`（生产推荐，天然无跨域）。
- 设为绝对地址（如 `http://host:8000`）→ 浏览器直连后端（需后端可被公网访问）。

本项目生产环境用 Nginx（`/etc/nginx/conf.d/cloudpg.conf`）：`/` → `:3002`，
`/api/` → `127.0.0.1:8000`，因此前端 `NEXT_PUBLIC_API_BASE` 留空即可。

**Web 控制台功能**：

| 页面 | 能力 |
| --- | --- |
| 登录 | 账密登录（User 通道，签发 Session JWT） |
| 概览 | 项目 / 数据库 / 备份统计 |
| 数据库 | 创建 / 删除 / SQL 控制台（自动 resume） |
| 数据表 | 浏览数据表 / 查看表内容 |
| **PG性能** | 管理提升性能的扩展(插件)（列表/安装/卸载）+ 调整运行参数（数据库级 / 实例级） |
| 计算实例 | 启停 / 挂起 / 恢复 / 调规格 (0.5~4 CPU) |
| 连接 & 角色 | 连接串 / 多语言片段 / 角色管理 |
| 备份 | 手动备份 / 恢复 |
| 监控 | 8 项核心指标 + 自动刷新 |
| 日志 | 数据库 / 计算实例运行日志 |
| 设置 | 项目与平台设置 |


### 管理后台访问（当前 VPS 实际部署）

- 控制台地址：http://217.69.2.217:3002/login
- 反向代理（Nginx `/etc/nginx/conf.d/cloudpg.conf`）：`/` → `127.0.0.1:3002`（前端），`/api/` → `127.0.0.1:8000`（后端）。
- 后端进程绑 `127.0.0.1:8000`，前端 `npx next start -p 3002`。

**Web 控制台登录凭据（User 通道，账密）**：

```text
邮箱：admin@cloudpg.local
密码：CloudPG@2026
```

> 由 `python -m db.seed_admin --email admin@cloudpg.local --password 'CloudPG@2026' --org acme --org-name 'Acme Inc'` 创建。

**Agent 通道（CLI / SDK，X-API-Key）**：

```text
X-API-Key：org_acme__proj_<projId>__<rand>
```

> `<projId>` 为该组织默认项目的 id，seed 时一并生成并打印在终端（形如
> `X-API-Key (agent): org_acme__proj_xxxx__yyyy`）。CLI/SDK 用此 Key 调用，
> 与 Web 账密登录互相独立。

登录后前端把 Session JWT 存入 `localStorage`，后续请求自动带 `Authorization: Bearer <JWT>`。

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

### 认证端点（User 通道）

| 方法 & 路径 | 说明 |
| --- | --- |
| `POST /api/v1/auth/login` | 账密登录 `{email, password}` → 返回 `{access_token, token_type, user}` |
| `GET  /api/v1/auth/me` | 当前用户上下文（需 Bearer JWT） |
| `POST /api/v1/auth/logout` | 登出（无状态 JWT，前端删除 token 即可） |

Session JWT payload 字段：`sub`(user_id)、`organization_id`、`project_id`、`typ:"user"`、`iat`、`exp`(默认 1 天)。

### 资源端点

| 资源 | 主要端点 |
| --- | --- |
| 项目 | `GET/POST /api/v1/projects`、`GET /api/v1/projects/{id}/connection-string` |
| 数据库 | `GET/POST /api/v1/databases`、`DELETE /api/v1/databases/{id}`、`POST /api/v1/databases/{id}/query` |
| 计算 | `POST /api/v1/computes/{id}/{start\|stop\|suspend\|resume\|restart}`、`PATCH /api/v1/computes/{id}` |
| 角色 | `GET/POST /api/v1/projects/{id}/roles`、`POST /api/v1/projects/{id}/roles/{rid}/reset-password`、`DELETE ...` |
| 备份 | `GET/POST /api/v1/backups`、`POST /api/v1/backups/{id}/restore` |
| 监控 | `GET /api/v1/metrics/databases/{id}` |
| PG性能 | `GET /api/v1/performance/extensions`、`POST /api/v1/performance/extensions`、`DELETE /api/v1/performance/extensions/{name}`、`GET/POST /api/v1/performance/settings` |

详见 `docs/PRD.md`、`docs/TODO.md` 与 `docs/VERIFY.md`（真实端到端验证手册）。

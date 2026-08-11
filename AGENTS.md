# AGENTS.md（中文）

本文件为 AI 编程助手 / 协作者提供 CloudPG 项目的关键上下文与约定。修改代码前请先阅读。

## 项目概览

CloudPG 是一个 **AI-Native Serverless PostgreSQL 云数据库平台（MVP）**，在裸 VPS 上用进程管理拉起 PostgreSQL 实例（不使用 Kubernetes）。Control Plane 与用户数据库完全分离。

- **Control Plane**：FastAPI + SQLAlchemy(async) + asyncpg，管理数据库/计算/存储/连接/备份/监控生命周期。
- **Web 控制台**：Next.js 16 + TypeScript + Tailwind CSS v4。
- **CLI / SDK**：Python（`apps/cli/cloudpg.py`、`packages/sdk-python`）。

## 目录结构

```text
apps/
  api/      FastAPI Control Plane（主入口 apps/api/main.py）
  cli/      cloudpg CLI
  web/      Next.js 管理后台
db/         models / session / init_db / seed_admin（SQLAlchemy 模型与迁移）
managers/   database_manager / compute_manager / storage_manager
services/   服务层（project/compute/database/endpoint/backup/metrics）
deploy/     systemd 模板与脚本
packages/   sdk-python
dev/        docker-compose 本地对齐
docs/       PRD.md / TODO.md / VERIFY.md
```

## 鉴权（双通道，务必理解）

`apps/api/security.py` 的 `require_auth` 同时支持两类凭证，统一产出 `AuthContext(actor, user_id, organization_id, project_id)`：

| 通道 | actor | 凭证 | 来源 |
| --- | --- | --- | --- |
| **User** | `user` | `Authorization: Bearer <Session JWT>` | Web 控制台账密登录后由 FastAPI 签发 |
| **Agent** | `agent` | `X-API-Key`（格式 `org_<org>__proj_<proj>__<rand>`） | CLI / SDK |

关键约定：
- **账密只用 bcrypt 校验**（`apps/api/routers/auth.py`）。注意：当前环境 `bcrypt 5.x` 与 `passlib` 不兼容，代码已改用 `bcrypt` 库直接 `hashpw`/`checkpw`，**不要改回 passlib**。
- **Session JWT** 用 `JWT_SECRET`（HMAC-SHA256，默认 HS256）签发，payload 含 `sub`/`organization_id`/`project_id`/`typ:"user"`/`exp`(1 天)。JWT 的租户声明只来自服务端签名，FastAPI 绝不信任前端传入的租户信息。
- 新增需要登录的接口时，依赖 `require_auth` 即可拿到 `AuthContext`，不要自行解析租户。

认证端点：`POST /api/v1/auth/login`、`GET /api/v1/auth/me`、`POST /api/v1/auth/logout`。

## 数据模型约定

- 多租户隔离字段来自 `db/base.py` 的 `TenantMixin`：`organization_id` + `project_id`（NOT NULL）。
- `Project` 模型自身也带 `project_id`，seed/创建时填为自身 id（自引用隔离）。
- ID 生成用 `db.base.gen_id(prefix)`（如 `gen_id("org")`）。

## 开发与部署命令

### 后端（Python venv 在 `.venv/`）

```bash
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m db.init_db                       # 初始化 Control Plane 表
.venv/bin/python -m db.seed_admin \
  --email admin@cloudpg.local --password 'CloudPG@2026' \
  --org acme --org-name 'Acme Inc'                   # 创建管理员+组织+默认项目+Agent Key
.venv/bin/uvicorn apps.api.main:app --host 127.0.0.1 --port 8000
```

### Web 前端（`apps/web`）

```bash
cd apps/web && npm install
npm run dev            # 开发 :3000
npm run build && npm run start -- -p 3002   # 生产 :3002
```

前端通过 `NEXT_PUBLIC_API_BASE` 决定后端地址：
- **留空（默认/生产）** → 同源相对路径 `/api/...`，由 Nginx（`/etc/nginx/conf.d/cloudpg.conf`）把 `/api/` 反代到 `127.0.0.1:8000`。
- 设为绝对地址 → 浏览器直连后端（需后端公网可达）。

前端 API 客户端在 `apps/web/src/lib/api.ts`：token 存 localStorage（`cloudpg_token`），请求自动带 `Authorization: Bearer`；`parseToken()` 仅读取 JWT payload claims（不验签）。

## 生产部署拓扑（当前 VPS）

- Nginx `cloudpg.conf`：`/` → `127.0.0.1:3002`（前端），`/api/` → `127.0.0.1:8000`（后端）。
- 后端进程绑 `127.0.0.1:8000`，前端绑 `:3002`。
- 修改后端代码后需重启 uvicorn；修改前端代码后需重新 `npm run build` 并重启 `npm run start`。

## 关键文件速查

| 关注点 | 文件 |
| --- | --- |
| 鉴权核心 | `apps/api/security.py` |
| 登录/登出 | `apps/api/routers/auth.py` |
| 路由注册 | `apps/api/main.py` |
| 配置（密钥/DB） | `apps/api/config.py`、`.env` |
| 数据模型 | `db/models.py`、`db/base.py` |
| 初始数据 | `db/seed_admin.py` |
| 前端 API 客户端 | `apps/web/src/lib/api.ts` |
| 前端登录页 | `apps/web/src/app/login/page.tsx` |

## 修改约定

- 新增 API 路由放在 `apps/api/routers/`，并在 `main.py` 用 `app.include_router(..., prefix="/api/v1")` 注册。
- 受保护接口统一依赖 `require_auth`（`AuthContext`），不要用明文 API Key 或 JWT 手工解析租户。
- 密码处理只用 `bcrypt` 库（`hash_password`/`verify_password`），不要引入 `passlib`。
- 前端改动后必须 `npm run build` 才能在 `:3002` 生效（`.env.local` 等 `NEXT_PUBLIC_*` 为构建期注入）。
- 所有凭证/密钥放 `.env`，两处共用 `JWT_SECRET`、`JWT_ALGORITHM`、`API_KEY_SECRET`。

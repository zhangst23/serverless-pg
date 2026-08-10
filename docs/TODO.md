# CloudPG 开发 TODO List

> 基于 PRD.md 整理。产品定位：**AI-Native Serverless PostgreSQL**。
> 部署方式：**本地裸 VPS + systemd**（不使用 Kubernetes）。
> 第一版**不做 Branch**，聚焦 6 大基础云数据库能力。
> 原则：从第一天起 **Control Plane 与 PostgreSQL Runtime 完全解耦**，用户 PG 与 Control Plane PG 完全分离。

---

## 0. 基础设施与底座（Phase 0）

目标：在本地裸 VPS 上跑通 `Create → Connect → Query → Delete`。

- [ ] 准备本地 VPS（Ubuntu/Debian），安装 PostgreSQL 18
- [ ] 安装并配置 PgBouncer（连接池）
- [ ] 安装并配置 Envoy（代理/路由入口）
- [ ] 准备对象存储（MinIO，用于 WAL Archive / Backup）
- [ ] 初始化 Control Plane 独立 PostgreSQL 实例（与用户 PG 隔离）
- [ ] systemd unit 模板（用于拉起/停止/重启 PG 进程）
- [ ] 验证：手动起一个 PG 实例，经 Envoy → PgBouncer 连上并跑 SQL

**里程碑**：裸 VPS 上的 PG 可创建、连接、查询、删除。

---

## 1. Control Plane 核心（Phase 1）

目标：达到 **Serverless PostgreSQL Cloud（基础能力完整）**。

### 1.1 后端骨架（FastAPI）
- [ ] 初始化 FastAPI + Pydantic + SQLAlchemy (async) + asyncpg（`apps/api`）
- [ ] Alembic 迁移框架接入
- [ ] Redis + Arq 任务队列接入（不用 Celery）
- [ ] 多租户隔离基类：`organization_id` / `project_id` 强制注入
- [ ] 鉴权中间件（API Key / JWT，暂可用自研轻量方案）
- [ ] OpenAPI 文档自动生成

### 1.2 资源模型与数据库表（Control Plane DB）
- [ ] `organizations` / `users` / `members`
- [ ] `projects`
- [ ] `databases`
- [ ] `computes`（vCPU 档位 / RAM / 状态机）
- [ ] `endpoints`（连接串）
- [ ] `backups` / `volumes` / `snapshots`
- [ ] `regions` / `nodes`
- [ ] `api_keys` / `subscriptions` / `usage`

### 1.3 Manager 层（裸机资源管理，managers/）
- [ ] **Database Manager**：建库 / 删库 / 列表（创建独立数据目录 + PG 实例）
- [ ] **Compute Manager**：Start / Stop / Restart / Resize / Suspend / Resume
  - [ ] 通过 systemd / 进程调用在 VPS 上实际操作系统资源
  - [ ] Compute 规格映射：0.25 / 0.5 / 1 / 2 / 4 CPU（cgroup 限制 CPU、内存）
- [ ] **Storage Manager**：容量配额、挂载点、扩容、数据目录布局
  - [ ] 档位：10 GB / 50 GB / 100 GB / 500 GB / 1 TB

### 1.4 服务层（services/）
- [ ] Project Service：增删改查
- [ ] Database Service（含 Lifecycle：Create / Start / Stop / Restart / Delete）
- [ ] Compute Service（生命周期状态机）
- [ ] Endpoint Service（生成 `postgres://...` 连接串）
- [ ] Backup Service（pgBackRest 对接）
- [ ] Metrics Service（指标采集接口）
- [ ] User Service / Billing Service（Compute / Storage / Transfer / Backup）

### 1.5 API 网关与路由（/api/v1）
- [ ] `POST /api/v1/projects`
- [ ] `POST /api/v1/databases`（Create）
- [ ] `POST /api/v1/computes/{id}/start`
- [ ] `POST /api/v1/computes/{id}/stop`
- [ ] `POST /api/v1/computes/{id}/restart`
- [ ] `DELETE /api/v1/databases/{id}`（Delete）
- [ ] `PATCH /api/v1/computes/{id}`（Resize）
- [ ] `POST /api/v1/databases/{id}/query`
- [ ] `organizations / computes / endpoints / backups / metrics / users / billing` 资源 CRUD

### 1.6 ① Database Lifecycle
- [ ] Create（建库 + 分配 Compute + 生成 Endpoint）
- [ ] Start
- [ ] Stop
- [ ] Restart
- [ ] Delete（释放资源、清理数据目录）

### 1.7 ② Serverless Compute
- [ ] Compute 规格档位：0.25 / 0.5 / 1 / 2 / 4 CPU
- [ ] 内存随 CPU 比例配置
- [ ] Idle 检测 → Suspend（释放 Compute 资源，停进程）
- [ ] Request（新连接到达）→ Resume（启动 PG，恢复就绪）
- [ ] 启停链路：Envoy / PgBouncer 连接到达 → 触发唤醒

### 1.8 ③ Storage
- [ ] 容量档位：10 / 50 / 100 / 500 GB / 1 TB
- [ ] Storage Manager 配额与挂载点管理
- [ ] 扩容能力（后续可增强）

### 1.9 ④ Connection
- [ ] PgBouncer 集成（session / transaction 池模式）
- [ ] Connection Pool 配置
- [ ] Connection Limit（每实例最大连接数）
- [ ] Envoy 入口代理/路由
- [ ] 生成标准连接串 `postgres://user:pass@host:5432/db`
- [ ] **DX**：连接页标注"暂停态首连延迟"，给出应用层重试 + 连接池预热最佳实践
- [ ] **DX**：文档明确 PgBouncer transaction 模式限制（SET / LISTEN / 临时表跨语句不支持）
- [ ] **DX**：按 project 支持"永不自动暂停"白名单（排除暂停）

### 1.10 ⑤ Backup
- [ ] pgBackRest 对接（WAL Archive → S3 / MinIO）
- [ ] Automatic Backup（定时自动备份）
- [ ] Manual Backup（手动触发）
- [ ] Restore（从备份恢复）
- [ ] PITR（基于 WAL 的时间点恢复）

### 1.11 ⑥ Monitoring
- [ ] 指标采集：CPU / RAM / Storage / Connections / QPS / TPS / IOPS / Latency
- [ ] Prometheus + VictoriaMetrics + Grafana 接入
- [ ] Metrics Service 暴露接口 `GET /metrics`
- [ ] 控制台指标面板
- [ ] **DX**：慢查询面板、最近错误、连接被拒原因
- [ ] **DX**：PG 日志流式查看（Loki → 控制台）

### 1.11.1 角色与凭证（DX）
- [ ] 创建多个 DB 角色（读写 / 只读），独立密码
- [ ] 控制台生成 / 重置密码，一键下载 `.env`
- [ ] 连接页按语言（Node / Python / Go / Rust）给出可复制连接代码
- [ ] 客户端兼容清单（psql / psycopg / node-pg / Prisma / Drizzle / SQLAlchemy）

### 1.11.2 导入导出（DX）
- [ ] 控制台 schema/data 导入导出
- [ ] CLI `cloudpg db dump | restore`，支持上传恢复

### 1.12 前端控制台（apps/console，Next.js + TS + Tailwind + shadcn/ui + TanStack Query）
- [ ] Dashboard / Projects 列表
- [ ] Project Detail → Overview
- [ ] SQL Editor（Monaco Editor）
- [ ] Tables 浏览
- [ ] Compute 管理（规格、启停、Suspend/Resume、暂停白名单开关）
- [ ] Storage 管理（容量档位）
- [ ] Backups 列表与恢复 / PITR
- [ ] Metrics 面板（8 项指标 + 慢查询）
- [ ] Connection 信息展示（多语言代码 + 连接串）
- [ ] Roles 管理（角色/密码/只读）
- [ ] Logs 查看（PG 日志流式）
- [ ] Settings

### 1.13 CLI（apps/cli，开发者友好）
- [ ] `cloudpg login / projects / databases / computes / sql` 基础命令
- [ ] `cloudpg db connect`：一键直连，无需手抄连接串
- [ ] `cloudpg db dump | restore`：导入导出
- [ ] `cloudpg logs`：查看 PG 日志
- [ ] `cloudpg link`：当前目录关联 project
- [ ] `cloudpg warm`：保活/预热
- [ ] shell 自动补全（bash / zsh / fish）
- [ ] 对接 `/api/v1`

### 1.14 SDK 与文档（DX）
- [ ] `packages/sdk-js` / `packages/sdk-python`：typed API（连接/查询/角色/启停 Compute），清晰报错
- [ ] OpenAPI + "5 分钟上手" + 各语言 Quickstart + `examples/` 示例仓库
- [ ] `dev/`：docker-compose 起最小 PG + PgBouncer，对齐云端行为（`cloudpg dev`）

**里程碑**：开发者可在控制台/CLI/API 创建 DB + Compute + Endpoint，连上 PG 跑 SQL；管理角色凭证、一键连接/导入导出/看日志；能启停/挂起恢复/调规格/备份恢复/PITR；看监控与慢查询；并用 SDK/文档快速上手。

---

## 2. Branching / Preview / Migrations（Phase 2，开发者友好核心，最高优先级）

- [ ] Snapshot 机制
- [ ] Clone
- [ ] Branch（父子关系）
- [ ] **Preview Database**：监听 Git PR 事件 → 自动建 Branch → 提供 PR Database
- [ ] **Migrations 推荐流程**：branch 上跑 migration → 验证 → 合并回 main
- [ ] PITR 增强
- [ ] **MCP Server 最小可用版**：inspect schema / run query / create branch（让 AI Agent 直接操作）

> 第一版明确跳过，见 PRD §13 / §23；但本阶段是开发者友好度最高的部分，优先级高于弹性与多实例。

---

## 3. 弹性与多实例（Phase 3，后续）

- [ ] Autoscaling（按 CPU / Mem / Conn / QPS）
- [ ] Read Replica
- [ ] HA：Patroni + etcd

---

## 4. Neon 级存储（Phase 4，后续）

- [ ] WAL Service
- [ ] Page Storage
- [ ] Copy-on-Write
- [ ] Instant Branch

---

## 5. AI-Native 能力与生态（Phase 5，后续）

- [ ] AI Agent 完整工作流：Inspect → Branch → Modify Schema → Migrate → Test → PR
- [ ] AI API：`POST /sql/query` `POST /migrations` `GET /schema` `GET /metrics`
- [ ] Schema Migration / Database Diff / Branch Merge 深化
- [ ] Git Integration 深化（PR Database 与 Preview 联动）

---

## 6. 跨阶段通用事项

- [ ] 监控栈：Prometheus + VictoriaMetrics + Grafana
- [ ] 日志：Loki
- [ ] SDK：`packages/sdk-js` / `packages/sdk-python`
- [ ] 类型包：`packages/types`
- [ ] CI/CD：GitHub Actions
- [ ] 多租户安全审计与配额
- [ ] 计费对账（usage 表与 Billing 服务）

---

## ❌ 第一版明确不做（避免范围蔓延）

- [ ] Kubernetes / K8s 编排
- [ ] Database Branch / Branching
- [ ] 自研 PostgreSQL
- [ ] 自研 WAL
- [ ] 自研分布式存储
- [ ] 多地域 / 全球数据库 / Edge Database
- [ ] 自研 SQL Proxy
- [ ] 自研 HA / 自研 Consensus
- [ ] 复杂 Autoscaling
- [ ] Git Integration / Preview Database
- [ ] AI Agent / MCP 完整工作流

---

## 建议执行顺序

```text
Phase 0  →  Phase 1                 →  Phase 2                      →  Phase 3/4/5
底座跑通     6 大基础能力 + 开发者体验     Branching/Preview/Migrations/MCP     弹性/Neon存储/AI-Native
```

Phase 1 完成即形成"开发者友好"的可用产品（含角色凭证、CLI、导入导出、慢查询、SDK）；
Phase 2 是开发者友好度最高的阶段（预览库、PR 自动建库、AI Agent 可操作），优先级高于弹性与多实例。

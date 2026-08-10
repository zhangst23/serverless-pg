从零做一个 Neon 类 Serverless PostgreSQL 平台**，我建议不要把它理解成"自己写一个 PostgreSQL"，而是：

> **PostgreSQL 原生数据库 + 自研 Control Plane + Compute 管理 + Storage 层**

下面给你一版适合直接交给 AI IDE 开发的初版产品策划/技术方案。

---

# CloudPG 产品策划文档

## 1. 产品定位

### 产品名称

暂定：**CloudPG**

定位：

> 面向 SaaS、AI Agent、开发者和现代 Web 应用的 Serverless PostgreSQL 云数据库平台。

核心体验参考：

* Neon：Serverless PostgreSQL / Branching
* Supabase：Database API / Auth / Realtime
* Netlify：Preview Database / AI Agent Workflow
* Vercel：Developer Experience

第一阶段**只做 PostgreSQL**，不做 SQLite、MySQL。

---

# 2. 第一版核心产品能力（MVP）

第一版聚焦云数据库最基础的 6 大能力，**不包含 Branch**：

```text
① Database Lifecycle
   Create / Start / Stop / Restart / Delete

② Serverless Compute
   规格：0.25 / 0.5 / 1 / 2 / 4 CPU
   自动：Idle → Suspend → Request → Resume

③ Storage
   10 GB / 50 GB / 100 GB / 500 GB / 1 TB

④ Connection
   postgres://user:pass@host:5432/db
   支持 PgBouncer / Connection Pool / Connection Limit

⑤ Backup
   Automatic Backup / Manual Backup / Restore / PITR

⑥ Monitoring
   CPU / RAM / Storage / Connections / QPS / TPS / IOPS / Latency
```

### 后续阶段能力（非第一版）

```text
Database Branch        (后续)
Instant Clone          (后续)
Copy-on-Write Storage  (后续)
Distributed Storage    (后续)
Multi-region           (后续)
Read Replica           (后续)
Autoscaling            (后续)
Git Integration        (后续)
Preview Database       (后续)
AI Agent / MCP         (后续)
```

---

# 3. 产品核心模型

采用 Neon 类资源模型（第一版去掉 Branch）：

```text
Organization
    │
    └── Project
          │
          ├── Storage
          │
          ├── Compute
          │
          ├── Endpoint
          │
          ├── Database
          │
          ├── Backup
          │
          └── API Key
```

例如：

```text
Project: shop

Production
├── Compute
│   ├── 1 vCPU
│   └── 2 GB RAM
│
├── Database
│   └── shop
│
└── Endpoint
    └── postgres://...
```

---

# 4. 总体技术架构（本地裸 VPS）

```text
                         User
                           │
                           ▼
                       Next.js
                           │
                           ▼
                        FastAPI
                           │
                  ┌────────┴────────┐
                  │  Control Plane  │
                  └────────┬────────┘
                           │
                    Database Manager
                           │
                    Compute Manager
                           │
                    Storage Manager
                           │
                           ▼
                        VPS (裸机)
                           │
             ┌─────────────┼─────────────┐
             ▼             ▼             ▼
           PG-01         PG-02         PG-03
             │
          PgBouncer
             │
           Envoy
```

说明：

* 不使用 Kubernetes。直接在本地裸 VPS 上用 systemd / 进程管理拉起 PostgreSQL 实例。
* `PG-01 / PG-02 / PG-03` 表示运行在同一 VPS（或不同 VPS 节点）上的多个 PostgreSQL 实例。
* 三个 Manager 是 Control Plane 内部模块，负责把 API 请求翻译成对 PG 进程/数据目录/连接层的实际操作。
* 连接入口：`Envoy`（代理/路由）→ `PgBouncer`（连接池）→ `PostgreSQL`。

---

# 5. 技术栈

## Control Plane 后端

**Python + FastAPI**

原因：

* PostgreSQL 生态成熟
* 异步 API
* 云/系统运维 SDK 丰富
* AI Agent 集成方便
* 适合快速开发 Control Plane

核心：

```text
FastAPI
Pydantic
SQLAlchemy
asyncpg
Alembic
Redis
Arq        (不用 Celery)
```

---

# 6. Control Plane 数据库

使用：**PostgreSQL**，但与用户 PostgreSQL 完全分离。

```text
Control Plane DB
│
├── organizations
├── users
├── projects
├── databases
├── computes
├── endpoints
├── backups
├── volumes
├── regions
├── nodes
├── api_keys
├── subscriptions
└── usage
```

---

# 7. 前端

```text
Next.js
TypeScript
React
Tailwind CSS
shadcn/ui
TanStack Query
Monaco Editor
```

控制台：

```text
Dashboard
Projects
Project Detail
├── Overview
├── SQL Editor
├── Tables
├── Compute
├── Storage
├── Backups
├── Metrics
├── Connection
└── Settings
```

---

# 8. PostgreSQL Compute Layer

每个 Compute 实例：

```text
Compute
│
├── PostgreSQL
├── PostgreSQL extensions
├── PgBouncer
├── Metrics exporter
└── Agent
```

例如：

```text
compute-001
├── PostgreSQL 18
├── PgBouncer
└── node-agent
```

### Serverless Compute 规格

第一版支持的 Compute 档位：

```text
0.25 CPU
0.5  CPU
1    CPU
2    CPU
4    CPU
```

内存随 CPU 比例配置（如 0.25 CPU → 0.5 GB，1 CPU → 2 GB，以此类推）。

### 自动挂起 / 恢复

```text
Idle
 ↓
Suspend (Compute 资源释放，进程停止)
 ↓
Request (新连接到达)
 ↓
Resume (启动 PostgreSQL，恢复就绪)
```

第一版先做 Auto Suspend / Auto Resume，验证启停链路；Scale-to-zero 的极致优化后续再做。

---

# 9. 不使用 Kubernetes，使用本地裸 VPS

采用：

> **本地裸 VPS + systemd / 进程管理**

原因：

* 第一版目标是跑通云数据库基础能力，不引入 K8s 编排复杂度。
* 直接在 VPS 上用 systemd unit / 自研 Manager 拉起、停止、重启 PostgreSQL 进程。
* 数据目录放在本地 NVMe / SSD，备份归档到对象存储（S3 / MinIO）。
* 后续若需要多机编排，再考虑引入 K8s，但 Control Plane 接口保持不变。

每个 PostgreSQL Compute 实例对应：

```text
systemd unit / 进程
│
└── PostgreSQL (独立数据目录 + 端口)
```

注意：

> 不要直接把数据目录写死在某处就结束。后期 Storage 管理、Snapshot、Compute Migration 都需要 Storage Manager 统一规划路径与配额。

---

# 10. 自研 Manager 层（替代 Operator）

这是核心研发模块。因为不使用 K8s，把"Operator"改为**裸机上的 Manager 模块**：

暂定：

**CloudPG Manager**

包含：

```text
Database Manager   # 建库、删库、列表
Compute Manager    # 启停、重启、Resize、Suspend/Resume
Storage Manager    # 容量配额、挂载、扩容、归档
```

负责：

```text
Create PostgreSQL
Delete PostgreSQL
Start
Stop
Restart
Resize
Suspend
Resume
Backup
Restore
```

架构：

```text
Control Plane
      │
      ▼
  Manager API
      │
  ┌───┼─────────┐
  ▼   ▼         ▼
DB  Compute   Storage
```

Manager 通过 SSH / 本地进程调用 / systemd 在 VPS 上实际操作系统资源。

---

# 11. PostgreSQL 高可用（可选，后续）

第一版可单实例运行。后续如需 HA，使用成熟组件：

```text
PostgreSQL
+
Patroni
+
etcd
```

架构：

```text
              etcd
               │
       ┌───────┼───────┐
       ▼       ▼       ▼
     PG-01   PG-02   PG-03
    Primary  Replica Replica
       │       │       │
       └───────┼───────┘
               │
             Patroni
```

注意：Patroni 只负责 Leader / Failover / Replication；你的系统负责 Project / Compute / Storage / Billing / Lifecycle。

---

# 12. Connection Layer

用户连接：

```text
postgres://user:password@db.example.com:5432/db
```

入口：

```text
Internet
   │
Load Balancer / Envoy
   │
PgBouncer
   │
PostgreSQL
```

推荐：

```text
PgBouncer
+
Envoy
```

第一版支持：

```text
PgBouncer          # 连接池
Connection Pool    # 连接池模式 (session / transaction)
Connection Limit   # 每实例最大连接数限制
```

### 开发者友好的连接注意事项（DX）

> 这些是 Serverless + PgBouncer 最容易让开发者踩坑的点，必须在连接页和文档中显式说明。

```text
1. PgBouncer 事务模式 (transaction) 限制：
   - 不支持跨语句的 session 级特性：SET / LISTEN / NOTIFY / 临时表 / 预备语句跨事务
   - Prisma / Drizzle / SQLAlchemy 默认可工作，但用到上述特性需切 session 模式或避免

2. 冷启动延迟：
   - 实例处于 Suspend 时，第一个连接会触发 Resume，首连延迟约 1~10s
   - 连接页需明确标注"暂停态首连延迟"
   - 提供保活/预热手段（控制台排除暂停白名单、CLI warm、应用层连接池预热）

3. 自动暂停副作用：
   - 暂停会断开所有长连接、回滚未提交事务
   - 支持按 project 配置"永不自动暂停"白名单
```

---

# 13. Branching（第一版不做）

> **第一版明确不做 Branch。** 这是后续阶段的核心方向，但不在 MVP 范围内。

后续实现路径（仅供参考，不在本期交付）：

```text
Production
    │
    ▼
PostgreSQL Snapshot
    │
    ▼
Clone
    │
    ▼
New Compute
```

技术选型后续再定：`pg_basebackup` / ZFS / LVM / COW Storage。

---

# 14. Storage Layer

第一版容量档位：

```text
10 GB
50 GB
100 GB
500 GB
1 TB
```

实现：

```text
MVP: 本地 NVMe / SSD + S3 (备份归档)
```

Storage Manager 负责配额、挂载点、扩容、数据目录布局。

---

# 15. Backup

推荐：

```text
pgBackRest
```

备份：

```text
PostgreSQL
      │
      ▼
WAL Archive
      │
      ▼
S3 / MinIO
```

第一版支持：

```text
Automatic Backup   # 定时自动备份
Manual Backup      # 手动触发备份
Restore            # 从备份恢复
PITR               # 基于 WAL 的时间点恢复
```

---

# 16. Monitoring

推荐：

```text
Prometheus
+
VictoriaMetrics
+
Grafana
```

指标：

```text
CPU
RAM
Storage
Connections
QPS
TPS
IOPS
Latency
```

用户看到：

```text
Database Metrics

CPU        32%
RAM        2.4 GB
Storage    28 GB
Connections 82
QPS        1,284
TPS        642
IOPS       156
Latency    12 ms
```

---

# 17. AI Agent 能力（后续预留）

从产品第一天就预留接口，但第一版不实现完整 Agent 工作流。

后续提供：

```text
Database MCP Server
```

API（后续）：

```text
POST /branches
POST /sql/query
POST /migrations
GET /schema
GET /metrics
```

---

# 18. API 设计

```text
/api/v1
│
├── organizations
├── projects
├── databases
├── computes
├── endpoints
├── backups
├── metrics
├── users
└── billing
```

创建项目：

```http
POST /api/v1/projects
```

调整 Compute：

```http
PATCH /api/v1/computes/{id}
```

执行 SQL：

```http
POST /api/v1/databases/{id}/query
```

数据库生命周期：

```http
POST   /api/v1/databases         # Create
POST   /api/v1/computes/{id}/start
POST   /api/v1/computes/{id}/stop
POST   /api/v1/computes/{id}/restart
DELETE /api/v1/databases/{id}    # Delete
```

角色与凭证（开发者友好）：

```http
POST   /api/v1/projects/{id}/roles        # 创建 DB 角色（可指定只读/读写）
POST   /api/v1/projects/{id}/roles/{rid}/reset-password
DELETE /api/v1/projects/{id}/roles/{rid}
GET    /api/v1/projects/{id}/connection-string   # 生成多语言连接片段 / .env
```

数据导入导出：

```http
POST   /api/v1/databases/{id}/dump         # 触发 pg_dump
POST   /api/v1/databases/{id}/restore-upload   # 上传并恢复
```

---

# 19. 多租户架构

Control Plane：

```text
Organization
   │
   ├── Members
   ├── Projects
   ├── API Keys
   └── Billing
```

Project：

```text
Project
│
├── Database
├── Compute
├── Endpoint
└── Storage
```

所有资源必须：

```text
organization_id
project_id
```

进行隔离。

---

# 20. 计费模型

采用：

```text
Compute
+
Storage
+
Data Transfer
+
Backup
```

例如：

```text
Compute   $ / vCPU-hour
Memory    $ / GB-hour
Storage   $ / GB-month
Transfer  $ / GB
Backup    $ / GB-month
```

---

# 21. 推荐技术栈总表

| 层                  | 技术                   |
| ------------------ | -------------------- |
| Frontend           | Next.js              |
| UI                 | Tailwind + shadcn/ui |
| API                | FastAPI              |
| Control DB         | PostgreSQL           |
| ORM                | SQLAlchemy           |
| Queue              | Redis + Arq          |
| 部署方式            | 本地裸 VPS + systemd  |
| PostgreSQL         | PostgreSQL 18        |
| HA (后续)          | Patroni + etcd       |
| Connection         | PgBouncer            |
| Proxy              | Envoy                |
| Manager            | Python (Control Plane 内) |
| Storage MVP        | NVMe/SSD + S3        |
| Backup             | pgBackRest           |
| Metrics            | Prometheus           |
| Long-term Metrics  | VictoriaMetrics      |
| Visualization      | Grafana              |
| Object Storage     | S3 / MinIO           |
| Logs               | Loki                 |
| Auth               | Keycloak / 自研        |
| API Docs           | OpenAPI              |
| CLI                | Go / Python          |
| SDK                | TypeScript / Python  |
| 本地对齐           | cloudpg dev (docker-compose 最小 PG) |
| 文档               | OpenAPI + Quickstart + 示例仓库 |
| AI (后续)          | MCP                  |
| CI/CD              | GitHub Actions       |

---

# 22. 项目目录

```text
cloudpg/
│
├── apps/
│   ├── console/                 # Next.js
│   ├── api/                     # FastAPI (Control Plane)
│   ├── worker/                  # Async Jobs (Arq)
│   └── cli/                     # CLI
│
├── services/
│   ├── project/
│   ├── database/
│   ├── compute/
│   ├── storage/
│   ├── backup/
│   ├── endpoint/
│   ├── billing/
│   └── metrics/
│
├── managers/                    # 裸机资源管理层
│   ├── database_manager/
│   ├── compute_manager/
│   └── storage_manager/
│
├── components/
│   ├── connection-router/
│   ├── postgres-agent/
│   └── backup-agent/
│
├── deploy/
│   ├── systemd/                 # systemd unit 模板
│   └── scripts/                 # 安装/初始化脚本
│
├── packages/
│   ├── types/
│   ├── sdk-js/
│   └── sdk-python/
│
├── mcp/                         # 后续
│   └── database-server/
│
├── dev/                         # 本地开发对齐 (docker-compose 最小 PG + PgBouncer)
│
├── examples/                    # 各语言 Quickstart 示例仓库
│
├── migrations/
│
└── docs/
```

---

# 23. 第一版不要做的东西

第一版**不要做**：

```text
❌ Kubernetes / K8s 编排
❌ Database Branch / Branching
❌ 自研 PostgreSQL
❌ 自研 WAL
❌ 自研分布式存储
❌ 多地域 / 全球数据库 / Edge Database
❌ 自研 SQL Proxy
❌ 自研 HA / 自研 Consensus
❌ 复杂 Autoscaling
❌ Git Integration / Preview Database
❌ AI Agent / MCP 完整工作流
```

第一版只做到：

```text
PostgreSQL
+
裸 VPS (systemd)
+
Control Plane
+
Database Lifecycle
+
Serverless Compute (Suspend/Resume + 规格)
+
Storage (容量档位)
+
Connection (PgBouncer + Pool + Limit)
+
Backup (Auto/Manual/Restore/PITR)
+
Monitoring
```

已经可以形成一个非常不错的云数据库产品。

---

# 24. 推荐研发路线

### Phase 0：底座跑通

```text
本地 VPS
PostgreSQL 18
PgBouncer
Envoy
```

验证：

```text
Create → Connect → Query → Delete
```

### Phase 1：Control Plane + 6 大基础能力 + 开发者体验基础（第一版目标）

完成：

```text
Project / Database / Compute / Endpoint
Database Lifecycle (Create/Start/Stop/Restart/Delete)
Serverless Compute (0.25~4 CPU, Auto Suspend/Resume)
Storage (10GB~1TB 档位)
Connection (PgBouncer + Pool + Limit)
Backup (Auto/Manual/Restore/PITR)
Monitoring (CPU/RAM/Storage/Conn/QPS/TPS/IOPS/Latency)
Dashboard / API / CLI
角色与凭证管理 (roles / 重置密码 / 连接串生成)
CLI: connect / dump / restore / logs / 自动补全
导入导出 (pg_dump / 上传恢复)
慢查询与 PG 日志可见 (Loki → 控制台)
冷启动说明 + 保活 + 排除暂停白名单
客户端兼容清单 (psql/psycopg/node-pg/Prisma/Drizzle/SQLAlchemy)
```

达到：

> **Serverless PostgreSQL Cloud（基础能力 + 开发者体验完整）**

### Phase 2：Branching / Preview / Migrations（开发者友好核心，最高优先级）

```text
Snapshot
Clone
Branch
Preview Database (Git PR 自动建库)
Migrations 推荐流程 (branch 上跑 migration → 验证 → 合并)
PITR 增强
```

> 这是开发者友好度最高的阶段：预览库、测试库、PR 自动建库应作为本阶段重点而非推迟。

### Phase 3：弹性与多实例

```text
Autoscaling
Read Replica
HA (Patroni + etcd)
```

### Phase 4：Neon 级存储

```text
WAL Service
Page Storage
Copy-on-Write
Instant Branch
```

### Phase 5：AI-Native

```text
AI Agent
MCP
Git Integration
Preview Database
```

---

## 最终产品定位

**AI-Native Serverless PostgreSQL**

核心产品模型：

```text
                  CloudPG
                     │
       ┌─────────────┼─────────────┐
       ▼             ▼             ▼
   PostgreSQL     Serverless     Connection
       │             │             │
       └─────────────┼─────────────┘
                     ▼
                 Storage / Backup
                     │
                     ▼
                  Monitoring
```

最核心的技术护城河不是 PostgreSQL 本身，而是你自己的 `Control Plane + Compute Manager + Storage Manager + Connection Layer`。

从第一天起把 `Control Plane` 和 `PostgreSQL Runtime` 完全解耦。这样即使第一版 PostgreSQL Runtime 用裸 VPS + systemd 跑，未来换成 K8s 或自研 Compute + WAL + Page Storage，也不会影响上层 API 和产品。

---

# 开发者体验（DX）专项设计

> 目标：做一个**开发者友好**的 Serverless PostgreSQL 云服务。以下为贯穿各阶段、需优先保障的 DX 能力。

## DX-1 凭证与角色（MVP）
- 支持创建多个 DB 角色（读写 / 只读），独立密码。
- 控制台可生成 / 重置密码，一键下载 `.env` 片段。
- 连接页按语言（Node / Python / Go / Rust）给出可复制连接代码。

## DX-2 客户端兼容（MVP）
- 保证 `psql` / `psycopg` / `node-pg` / `Prisma` / `Drizzle` / `SQLAlchemy` 直接连得上。
- 文档维护"已验证客户端清单"及已知限制（见 §12 事务模式限制）。

## DX-3 CLI 体验（MVP）
- `cloudpg db connect`：一键直连，无需手抄连接串。
- `cloudpg db dump | restore`：导入导出。
- `cloudpg logs`：查看 PG 日志。
- `cloudpg link`：把当前目录关联到某 project。
- shell 自动补全（bash / zsh / fish）。

## DX-4 冷启动与暂停（MVP）
- 连接页标注"暂停态首连延迟"。
- 提供保活/预热：排除暂停白名单、CLI `warm`、应用层连接池预热。
- 文档给出"重试 + 连接池预热"最佳实践。

## DX-5 可观测性对开发者可见（MVP）
- 慢查询面板、最近错误、连接被拒原因。
- PG 日志流式查看（Loki → 控制台）。

## DX-6 导入导出（MVP）
- 控制台支持 schema/data 导入导出。
- CLI 支持 `pg_dump` / 上传恢复。

## DX-7 SDK 与文档（MVP）
- `sdk-js` / `sdk-python` 提供 typed API：创建连接、执行查询、管理角色、启停 Compute，清晰报错。
- OpenAPI + "5 分钟上手" + 各语言 Quickstart + 示例仓库（`examples/`）。

## DX-8 本地开发对齐（MVP/Phase 2）
- `cloudpg dev` / `dev/` 目录用 docker-compose 起最小 PG + PgBouncer，对齐云端连接池行为，避免"本地能跑线上挂"。

## DX-9 Branching / Preview / MCP（Phase 2/3，提前）
- Branching + Preview Database（PR 自动建库）作为 Phase 2 最高优先级。
- MCP Server 最小可用版（inspect schema / run query / create branch）尽早提供，让 AI Agent 直接操作数据库。

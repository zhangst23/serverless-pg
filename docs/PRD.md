从零做一个 Neon 类 Serverless PostgreSQL 平台**，我建议不要把它理解成“自己写一个 PostgreSQL”，而是：

> **PostgreSQL 原生数据库 + 自研 Control Plane + Compute 管理 + Branching + WAL/Storage 层**

下面给你一版适合直接交给 AI IDE 开发的初版产品策划/技术方案。

---

# Serverless PostgreSQL Cloud 产品策划文档

## 1. 产品定位

### 产品名称

暂定：

**CloudPG**

定位：

> 面向 SaaS、AI Agent、开发者和现代 Web 应用的 Serverless PostgreSQL 云数据库平台。

核心体验参考：

* Neon：Serverless PostgreSQL / Branching
* Supabase：Database API / Auth / Realtime
* Netlify：Preview Database / AI Agent Workflow
* Vercel：Developer Experience

第一阶段**只做 PostgreSQL**，不做 SQLite、MySQL。

---

# 2. 核心产品能力

### MVP

```text
Project
Database
Compute
Connection
SQL Editor
Backup
Restore
Monitoring
API
```

### V1

```text
Database Branch
Instant Clone
PITR
Auto Suspend
Auto Resume
Compute Resize
Connection Pool
Database Metrics
```

### V2

```text
Git Integration
Preview Database
AI Agent Database
Schema Migration
Database Diff
Branch Merge
Database API
```

### V3

```text
Distributed Storage
Multi-region
Read Replica
Autoscaling
Scale-to-zero
Serverless Compute
```

---

# 3. 产品核心模型

不要采用：

```text
服务器 → PostgreSQL
```

而采用 Neon 类资源模型：

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
          ├── Branch
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
│   ├── 2 vCPU
│   └── 4 GB RAM
│
├── Database
│   └── shop
│
└── Endpoint
    └── postgres://...

Branches
├── development
├── staging
└── ai-agent-001
```

---

# 4. 总体技术架构

```text
                         Internet
                            │
                    ┌───────┴───────┐
                    │   API Gateway │
                    │     Envoy    │
                    └───────┬───────┘
                            │
                    ┌───────▼───────┐
                    │ Control Plane │
                    │    FastAPI    │
                    └───────┬───────┘
                            │
       ┌────────────────────┼────────────────────┐
       │                    │                    │
       ▼                    ▼                    ▼
 Project Service       Compute Service      Branch Service
 Database Service      Storage Service      Backup Service
 Billing Service       User Service         Metrics Service
       │                    │                    │
       └────────────────────┼────────────────────┘
                            │
                    ┌───────▼───────┐
                    │   Scheduler   │
                    │   Controller  │
                    └───────┬───────┘
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
        Compute Node    Compute Node   Compute Node
              │             │             │
              ▼             ▼             ▼
         PostgreSQL     PostgreSQL     PostgreSQL
              │             │             │
              └─────────────┼─────────────┘
                            │
                           WAL
                            │
                    ┌───────▼───────┐
                    │ Storage Layer │
                    │  S3 / MinIO  │
                    └───────────────┘
```

---

# 5. 技术栈

## Control Plane

### 后端

**Python + FastAPI**

原因：

* PostgreSQL 生态成熟
* 异步 API
* Kubernetes/云基础设施 SDK 丰富
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
Celery / Arq
```

我更推荐：

```text
FastAPI
+
asyncio
+
Arq
```

而不是一开始引入 Celery。

---

# 6. Control Plane 数据库

使用：

**PostgreSQL**

但注意：

> Control Plane PostgreSQL 和用户 PostgreSQL 必须完全分离。

```text
Control Plane DB
│
├── organizations
├── users
├── projects
├── databases
├── computes
├── branches
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

推荐：

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
├── Branches
├── Compute
├── Storage
├── Backups
├── Metrics
├── Connection
└── Settings
```

---

# 8. PostgreSQL Compute Layer

这里是整个系统的核心。

每个 Compute：

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

---

# 9. 不使用 Kubernetes 还是使用 Kubernetes？

我建议：

> **第一版使用 Kubernetes。**

因为你要做的是 Serverless Cloud，而不是单机 PostgreSQL 面板。

架构：

```text
Kubernetes
│
├── Control Plane
│
├── PostgreSQL Compute
│
├── Storage Controller
│
├── Branch Controller
│
└── Monitoring
```

每一个 PostgreSQL Compute：

```text
Pod
│
└── PostgreSQL
```

但是：

**不要直接使用 StatefulSet + PVC 就结束。**

因为后期 Branch、Snapshot、Compute Migration 都会受到限制。

---

# 10. 自研 PostgreSQL Operator

这是核心研发模块。

暂定：

**CloudPG Operator**

负责：

```text
Create PostgreSQL
Delete PostgreSQL
Start
Stop
Resize
Restart
Failover
Backup
Restore
Clone
Branch
Upgrade
Migration
```

架构：

```text
Control Plane
      │
      ▼
CloudPG API
      │
      ▼
CloudPG Operator
      │
 ┌────┼─────┐
 ▼    ▼     ▼
PG   PVC   Compute
```

---

# 11. PostgreSQL 高可用

第一版不要自己造数据库共识协议。

使用成熟组件：

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

但是要注意：

> Patroni 是 HA 组件，不是你的 Cloud Control Plane。

它只负责：

```text
Leader
Failover
Replication
```

你的系统负责：

```text
Project
Compute
Branch
Billing
Lifecycle
```

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
Load Balancer
   │
Connection Router
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

后期可以开发：

**Connection Router**

根据：

```text
Project
Branch
Region
Compute
```

动态路由。

---

# 13. Branching 是核心技术

这是产品最重要的研发方向之一。

用户：

```text
Production
```

点击：

> Create Branch

得到：

```text
production
   │
   ├── development
   ├── staging
   └── feature-login
```

API：

```http
POST /projects/{project_id}/branches
```

---

# 14. 第一阶段 Branch 实现

不要一开始挑战 Neon 的底层存储技术。

第一版：

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

可以使用：

```text
pg_basebackup
```

或者存储层：

```text
ZFS Snapshot
LVM Snapshot
Ceph Snapshot
CSI Snapshot
```

如果 Kubernetes：

```text
PostgreSQL
    │
   PVC
    │
VolumeSnapshot
    │
    ▼
Branch PVC
```

---

# 15. 第二阶段 Branch

研发：

**Copy-on-Write Storage**

架构：

```text
                Production
                    │
                Snapshot
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
      Dev        Staging      AI Agent
        │           │           │
        └───────────┼───────────┘
                    │
              Shared Base
```

数据不需要完整复制。

---

# 16. 第三阶段：真正的 Neon-like Storage

最终目标：

```text
PostgreSQL Compute
       │
       │ WAL
       ▼
WAL Service
       │
       ▼
Page Storage
       │
       ▼
Object Storage
```

例如：

```text
PostgreSQL
     │
     ▼
WAL
     │
     ▼
CloudPG Storage
     │
 ┌───┼────┐
 ▼   ▼    ▼
S3  MinIO Ceph
```

数据：

```text
Pages
WAL
Snapshots
Branches
```

统一存储。

---

# 17. Storage Layer

推荐分阶段：

### MVP

```text
Local NVMe
+
S3
```

### V1

```text
Ceph
```

### V2

```text
自研 Page Storage
+
Object Storage
```

---

# 18. Backup

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

支持：

```text
Full Backup
Incremental Backup
WAL Archive
PITR
Restore
```

---

# 19. Serverless

用户看到：

```text
Compute

0.25 - 16 vCPU
0.5 - 64 GB RAM
```

系统内部：

```text
Idle
 ↓
Suspend
 ↓
Compute = 0
```

访问：

```text
Connection
 ↓
Wake
 ↓
Start PostgreSQL
 ↓
Ready
```

但是：

> **MVP不要急着做真正的 Scale-to-zero。**

先做：

```text
Auto Suspend
Auto Resume
```

后面再优化启动时间。

---

# 20. Autoscaling

根据：

```text
CPU
Memory
Connections
QPS
IOPS
Latency
Storage
```

自动调整：

```text
0.25 CPU
   ↓
0.5 CPU
   ↓
1 CPU
   ↓
2 CPU
```

控制器：

```text
Metrics
   │
   ▼
Autoscaler
   │
   ▼
Compute Controller
   │
   ▼
Kubernetes
```

---

# 21. Monitoring

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
Memory
Disk
IOPS
Connections
QPS
TPS
Query latency
Cache hit
Replication lag
WAL
Storage
```

用户看到：

```text
Database Metrics

CPU        32%
Memory     2.4 GB
Connections 82
QPS        1,284
Latency    12ms
Storage    28 GB
```

---

# 22. AI Agent 能力

这个我建议从产品第一天就预留。

提供：

```text
Database MCP Server
```

例如 AI：

```text
Inspect database
     ↓
Inspect schema
     ↓
Create branch
     ↓
Modify schema
     ↓
Run migration
     ↓
Run SQL tests
     ↓
Create PR
```

API：

```text
POST /branches
POST /sql/query
POST /migrations
GET /schema
GET /metrics
```

未来可以支持：

```text
Claude
Codex
Cursor
VS Code
OpenAI Agents
```

---

# 23. Preview Database

非常重要。

例如 Git：

```text
Pull Request #128
       │
       ▼
CloudPG
       │
       ▼
Create Branch
       │
       ▼
PR Database
```

最终：

```text
PR #128
│
├── Application Preview
└── Database Preview
```

这就是：

> **Netlify/Vercel Preview + Neon Branching**

---

# 24. API 设计

例如：

```text
/api/v1
│
├── organizations
├── projects
├── databases
├── computes
├── branches
├── endpoints
├── backups
├── snapshots
├── metrics
├── users
└── billing
```

创建项目：

```http
POST /api/v1/projects
```

创建 Branch：

```http
POST /api/v1/projects/{id}/branches
```

调整 Compute：

```http
PATCH /api/v1/computes/{id}
```

执行 SQL：

```http
POST /api/v1/databases/{id}/query
```

---

# 25. 多租户架构

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
├── Branch
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

# 26. 计费模型

建议不要单纯按数据库数量收费。

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
Compute
$ / vCPU-hour

Memory
$ / GB-hour

Storage
$ / GB-month

Transfer
$ / GB

Backup
$ / GB-month
```

这样未来 Serverless 才容易做。

---

# 27. 推荐技术栈总表

| 层                  | 技术                   |
| ------------------ | -------------------- |
| Frontend           | Next.js              |
| UI                 | Tailwind + shadcn/ui |
| API                | FastAPI              |
| Control DB         | PostgreSQL           |
| ORM                | SQLAlchemy           |
| Queue              | Redis + Arq          |
| Container          | Kubernetes           |
| PostgreSQL         | PostgreSQL 18        |
| HA                 | Patroni              |
| Consensus          | etcd                 |
| Connection         | PgBouncer            |
| Proxy              | Envoy                |
| Operator           | Go                   |
| Scheduler          | Go                   |
| Storage MVP        | NVMe + S3            |
| Storage V1         | Ceph                 |
| Backup             | pgBackRest           |
| Metrics            | Prometheus           |
| Long-term Metrics  | VictoriaMetrics      |
| Visualization      | Grafana              |
| Object Storage     | S3 / MinIO           |
| Logs               | Loki                 |
| Auth               | Keycloak / 自研        |
| API Docs           | OpenAPI              |
| IaC                | Terraform Provider   |
| CLI                | Go                   |
| SDK                | TypeScript / Python  |
| AI                 | MCP                  |
| CI/CD              | GitHub Actions       |
| Container Registry | Harbor               |
| Deployment         | Helm                 |

---

# 28. 项目目录

我建议直接按照 Control Plane 思路设计：

```text
cloudpg/
│
├── apps/
│   ├── console/                 # Next.js
│   ├── api/                     # FastAPI
│   ├── scheduler/               # Scheduler
│   ├── worker/                  # Async Jobs
│   └── cli/                     # CLI
│
├── services/
│   ├── project/
│   ├── database/
│   ├── compute/
│   ├── branch/
│   ├── storage/
│   ├── backup/
│   ├── endpoint/
│   ├── billing/
│   └── metrics/
│
├── operators/
│   └── cloudpg-operator/        # Go
│
├── components/
│   ├── connection-router/
│   ├── storage-agent/
│   ├── postgres-agent/
│   └── backup-agent/
│
├── storage/
│   ├── snapshot/
│   ├── wal/
│   ├── pages/
│   └── object/
│
├── deploy/
│   ├── helm/
│   ├── kubernetes/
│   └── terraform/
│
├── packages/
│   ├── types/
│   ├── sdk-js/
│   └── sdk-python/
│
├── mcp/
│   └── database-server/
│
├── migrations/
│
└── docs/
```

---

# 29. MVP不要做的东西

这个非常重要。

第一版**不要做**：

```text
❌ 自研 PostgreSQL
❌ 自研 WAL
❌ 自研分布式存储
❌ 多地域
❌ 全球数据库
❌ Edge Database
❌ 自研 SQL Proxy
❌ 自研 HA
❌ 自研 Consensus
❌ 复杂 Autoscaling
```

第一版只做到：

```text
PostgreSQL
+
Kubernetes
+
Operator
+
Control Plane
+
Snapshot
+
Branch
+
Backup
```

已经可以形成一个非常不错的产品。

---

# 30. 推荐研发路线

### Phase 0

```text
Kubernetes
PostgreSQL
Patroni
PgBouncer
```

跑通：

```text
Create → Connect → Query → Delete
```

---

### Phase 1

完成：

```text
Project
Database
Compute
Endpoint
Backup
Monitoring
Dashboard
API
CLI
```

达到：

> **PostgreSQL Cloud**

---

### Phase 2

完成：

```text
Snapshot
Clone
Branch
PITR
Preview Database
```

达到：

> **Neon-like PostgreSQL**

---

### Phase 3

完成：

```text
Auto Suspend
Auto Resume
Autoscaling
Compute Resize
```

达到：

> **Serverless PostgreSQL**

---

### Phase 4

完成：

```text
Page Storage
WAL Service
Copy-on-Write
Instant Branch
```

达到：

> **真正的 Neon Architecture**

---

### Phase 5

完成：

```text
AI Agent
MCP
Git Integration
PR Database
Schema Migration
AI Database Agent
```

达到：

> **AI-native Serverless PostgreSQL**

---

## 最终我建议的产品定位

不要把它做成：

> “国产 Supabase”

也不要单纯做：

> “Neon 国产替代”

而是：

### **AI-Native Serverless PostgreSQL**

核心产品模型：

```text
                  CloudPG
                     │
       ┌─────────────┼─────────────┐
       ▼             ▼             ▼
   PostgreSQL     Branching     Serverless
       │             │             │
       └─────────────┼─────────────┘
                     ▼
                 AI Agent
                     │
             ┌───────┴───────┐
             ▼               ▼
          Git/PR          MCP/API
             │               │
             └───────┬───────┘
                     ▼
              Preview Database
```

**最核心的技术护城河不是 PostgreSQL 本身，而是你自己的 `Control Plane + Branching + Compute Scheduler + Storage Layer`。**

如果以这个方向开发，我会建议你**从第一天就把 `Control Plane` 和 `PostgreSQL Runtime` 完全解耦**。这样即使第一版 PostgreSQL Runtime 使用 Patroni/Kubernetes，未来换成你自己的 Compute + WAL + Page Storage，也不会影响上层 API 和产品。

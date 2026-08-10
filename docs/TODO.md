# CloudPG 开发 TODO List

> 基于 PRD.md 整理。产品定位：**AI-Native Serverless PostgreSQL**。
> 核心护城河 = `Control Plane + Branching + Compute Scheduler + Storage Layer`。
> 原则：从第一天起 **Control Plane 与 PostgreSQL Runtime 完全解耦**，用户 PG 与 Control Plane PG 完全分离。

---

## 0. 基础设施与底座（Phase 0）

目标：跑通 `Create → Connect → Query → Delete` 一条龙。

- [ ] 搭建本地 Kubernetes 集群（kind/k3d 或云上 EKS/GKE）
- [ ] 准备对象存储（MinIO，用于 WAL Archive / Backup）
- [ ] 部署 PostgreSQL 18 + Patroni + etcd 高可用底座（仅验证 HA，不作为 Control Plane）
- [ ] 部署 PgBouncer 连接池（连接层基础）
- [ ] 定义 Control Plane 独立 PostgreSQL 实例（与用户 PG 隔离）
- [ ] Helm / kustomize 基础部署模板（`deploy/`）
- [ ] 验证：在 K8s 上手动起一个 PG Pod，外部通过 PgBouncer 连上并跑 SQL

**里程碑**：裸 PG on K8s 可创建、连接、查询、删除。

---

## 1. Control Plane 核心（Phase 1）

目标：达到 **PostgreSQL Cloud**。

### 1.1 后端骨架（FastAPI）
- [ ] 初始化 FastAPI + Pydantic + SQLAlchemy (async) + asyncpg 项目结构（`apps/api`）
- [ ] Alembic 迁移框架接入
- [ ] Redis + Arq 任务队列接入（不用 Celery）
- [ ] 多租户隔离基类：`organization_id` / `project_id` 强制注入
- [ ] 鉴权中间件（API Key / JWT，暂可用自研轻量方案）
- [ ] OpenAPI 文档自动生成

### 1.2 资源模型与数据库表（Control Plane DB）
- [ ] `organizations` / `users` / `members`
- [ ] `projects`
- [ ] `databases`
- [ ] `computes`（vCPU / RAM / 状态机）
- [ ] `branches`（父子关系、源 branch）
- [ ] `endpoints`（连接串）
- [ ] `backups` / `volumes` / `snapshots`
- [ ] `regions` / `nodes`
- [ ] `api_keys` / `subscriptions` / `usage`

### 1.3 服务层（services/）
- [ ] Project Service：增删改查
- [ ] Database Service
- [ ] Compute Service（生命周期状态机：create/start/stop/resize/restart/delete）
- [ ] Endpoint Service（生成 `postgres://...` 连接串）
- [ ] Backup Service（pgBackRest 对接：全量/增量/WAL/PITR/Restore）
- [ ] Metrics Service（指标采集接口）
- [ ] User Service / Billing Service（计费维度：Compute / Storage / Transfer / Backup）

### 1.4 自研 Operator（operators/cloudpg-operator，Go）
- [ ] CloudPG API（接收 Control Plane 指令）
- [ ] 在 K8s 上 Create / Delete PostgreSQL Pod（**不直接用 StatefulSet+PVC 封死**，保留 Branch/Snapshot/Migration 扩展空间）
- [ ] Start / Stop / Restart / Resize
- [ ] Backup / Restore / Clone 钩子
- [ ] 与 Patroni 协作但不越界（HA 归 Patroni，Lifecycle 归 Operator）

### 1.5 API 网关与路由（/api/v1）
- [ ] `POST /api/v1/projects`
- [ ] `POST /api/v1/projects/{id}/branches`
- [ ] `PATCH /api/v1/computes/{id}`
- [ ] `POST /api/v1/databases/{id}/query`
- [ ] `organizations / databases / computes / branches / endpoints / backups / snapshots / metrics / users / billing` 资源 CRUD
- [ ] Envoy API Gateway 接入

### 1.6 前端控制台（apps/console，Next.js + TS + Tailwind + shadcn/ui + TanStack Query）
- [ ] Dashboard / Projects 列表
- [ ] Project Detail → Overview
- [ ] SQL Editor（Monaco Editor 接入）
- [ ] Tables 浏览
- [ ] Compute 管理
- [ ] Storage 概览
- [ ] Backups 列表与恢复
- [ ] Metrics 面板（接 Grafana 或自绘）
- [ ] Connection 信息展示
- [ ] Settings

### 1.7 CLI（apps/cli，Go）
- [ ] `cloudpg login / projects / databases / computes / branches / sql` 基础命令
- [ ] 对接 `/api/v1`

**里程碑**：用户可在控制台/CLI/API 创建 Project + Database + Compute + Endpoint，连上 PG 跑 SQL，并能备份恢复。

---

## 2. Branching 与快照（Phase 2）

目标：达到 **Neon-like PostgreSQL**。

- [ ] Snapshot 机制（MVP 用 `pg_basebackup` 或 K8s `VolumeSnapshot` / CSI Snapshot）
- [ ] Clone：从快照克隆出新 Compute
- [ ] `POST /projects/{project_id}/branches` 创建 Branch
- [ ] Branch 层级模型（production → development / staging / feature-*）
- [ ] Branch 独立 Endpoint（连接串隔离）
- [ ] PITR（基于 pgBackRest WAL Archive 的时间点恢复）
- [ ] Preview Database：监听 Git PR 事件 → 自动建 Branch → 提供 PR Database
- [ ] Git Integration 基础 Webhook（GitHub/GitLab）

**里程碑**：点一下 Create Branch，秒级（快照级）得到独立可写数据库。

---

## 3. Serverless 调度（Phase 3）

目标：达到 **Serverless PostgreSQL**。

- [ ] Auto Suspend（空闲超时自动挂起，Compute=0）
- [ ] Auto Resume（连接到达自动唤醒、启动 PG）
- [ ] Compute Resize（在线/离线扩缩 vCPU / RAM）
- [ ] 基础 Autoscaling 控制器（按 CPU / Memory / Connections / QPS 调节，避免过度复杂）
- [ ] Scheduler / Controller（Go，资源调度与生命周期编排）
- [ ] 连接唤醒链路：Connection → Wake → Start PG → Ready

**里程碑**：无流量时 Compute 归零计费，来流量自动恢复。

---

## 4. Neon 级存储层（Phase 4）

目标：达到 **真正的 Neon Architecture**。

- [ ] WAL Service（拦截 PG WAL 流）
- [ ] Page Storage（Pages / WAL / Snapshots / Branches 统一存储）
- [ ] Copy-on-Write（分支不再全量复制，共享 Base）
- [ ] Object Storage 对接（S3 / MinIO / Ceph）
- [ ] Instant Branch（COW 实现近乎瞬时建分支）
- [ ] 自研 Storage MVP 替换原来的 NVMe+快照方案

**里程碑**：分支几乎零成本、零拷贝创建，底层统一存储。

---

## 5. AI-Native 能力与生态（Phase 5）

目标：达到 **AI-Native Serverless PostgreSQL**。

- [ ] Database MCP Server（供 Claude / Codex / Cursor / VS Code / OpenAI Agents 调用）
- [ ] AI API：`POST /branches` `POST /sql/query` `POST /migrations` `GET /schema` `GET /metrics`
- [ ] Schema Migration 工具链
- [ ] Database Diff / Branch Merge
- [ ] AI Agent 工作流：Inspect → Branch → Modify Schema → Migrate → Test → PR
- [ ] Git Integration 深化（PR Database 与 Preview 联动）
- [ ] Database API（面向应用的直接 API）

**里程碑**：AI Agent 可自主 inspect schema、建分支、跑迁移、出 PR。

---

## 6. 跨阶段通用事项

- [ ] 监控栈：Prometheus + VictoriaMetrics + Grafana（CPU/Mem/Disk/IOPS/Conn/QPS/TPS/Latency/Cache/ReplLag/WAL/Storage）
- [ ] 日志：Loki
- [ ] SDK：`packages/sdk-js` / `packages/sdk-python`
- [ ] 类型包：`packages/types`
- [ ] Terraform Provider（IaC）
- [ ] CI/CD：GitHub Actions + Harbor 镜像仓库 + Helm 发布
- [ ] 多租户安全审计与配额
- [ ] 计费对账（usage 表与 Billing 服务）

---

## ❌ MVP 阶段明确不做（避免范围蔓延）

- [ ] 自研 PostgreSQL
- [ ] 自研 WAL
- [ ] 自研分布式存储
- [ ] 多地域 / 全球数据库 / Edge Database
- [ ] 自研 SQL Proxy
- [ ] 自研 HA / 自研 Consensus
- [ ] 复杂 Autoscaling

---

## 建议执行顺序

```text
Phase 0  →  Phase 1  →  Phase 2  →  Phase 3  →  Phase 4  →  Phase 5
底座跑通     云数据库     分支能力     弹性与休眠     Neon 存储      AI 原生
```

每阶段以"里程碑"为验收点，MVP 只需完成 Phase 0 + Phase 1 即可形成可用产品。

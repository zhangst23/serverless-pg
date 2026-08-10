"""CloudPG 资源模型 (Control Plane DB).

覆盖: organizations / users / members / projects / databases /
computes / endpoints / backups / volumes / api_keys / usage / roles
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base, TenantMixin, TimestampMixin, gen_id


# ---------- 账户 / 租户 ----------

class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: gen_id("org"))
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: gen_id("usr"))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)


class Member(Base, TimestampMixin):
    __tablename__ = "members"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: gen_id("mem"))
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="member")


# ---------- 项目 ----------

class Project(Base, TenantMixin, TimestampMixin):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: gen_id("proj"))
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    region: Mapped[str] = mapped_column(String(32), default="local")
    never_suspend: Mapped[bool] = mapped_column(Boolean, default=False)  # 排除自动暂停白名单


# ---------- 数据库实例 (Database Lifecycle) ----------

class Database(Base, TenantMixin, TimestampMixin):
    __tablename__ = "databases"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: gen_id("db"))
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    # 状态机: creating / active / suspended / stopping / deleting / error
    status: Mapped[str] = mapped_column(String(32), default="creating")
    compute_id: Mapped[str | None] = mapped_column(ForeignKey("computes.id"), nullable=True)
    endpoint_id: Mapped[str | None] = mapped_column(ForeignKey("endpoints.id"), nullable=True)


# ---------- 计算 (Serverless Compute) ----------

class Compute(Base, TenantMixin, TimestampMixin):
    __tablename__ = "computes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: gen_id("comp"))
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    # 规格档位 (vCPU): 0.25 / 0.5 / 1 / 2 / 4
    cpu: Mapped[float] = mapped_column(Float, default=1.0)
    memory_gb: Mapped[float] = mapped_column(Float, default=2.0)
    # 生命周期状态: provisioning / running / suspended / suspending / resuming / error
    status: Mapped[str] = mapped_column(String(32), default="provisioning")
    # 实际 PG 实例信息
    port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    data_dir: Mapped[str | None] = mapped_column(String(512), nullable=True)
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    auto_suspend: Mapped[bool] = mapped_column(Boolean, default=True)


# ---------- 连接入口 ----------

class Endpoint(Base, TenantMixin, TimestampMixin):
    __tablename__ = "endpoints"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: gen_id("ep"))
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, default=6432)
    pool_mode: Mapped[str] = mapped_column(String(16), default="transaction")  # session / transaction
    connection_limit: Mapped[int] = mapped_column(Integer, default=100)
    # 生成的标准连接串 postgres://user:pass@host:port/db
    connection_string: Mapped[str] = mapped_column(String(512), nullable=False)


# ---------- 角色 / 凭证 (DX) ----------

class Role(Base, TenantMixin, TimestampMixin):
    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: gen_id("role"))
    project_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    privilege: Mapped[str] = mapped_column(String(16), default="readwrite")  # readwrite / readonly
    password: Mapped[str] = mapped_column(String(255), nullable=False)


# ---------- 备份 / 存储 ----------

class Backup(Base, TenantMixin, TimestampMixin):
    __tablename__ = "backups"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: gen_id("bk"))
    database_id: Mapped[str] = mapped_column(ForeignKey("databases.id"), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), default="manual")  # automatic / manual
    status: Mapped[str] = mapped_column(String(32), default="running")  # running / completed / failed
    # 存储档位 (GB): 10 / 50 / 100 / 500 / 1024
    storage_gb: Mapped[int] = mapped_column(Integer, default=10)
    location: Mapped[str] = mapped_column(String(512), nullable=True)  # s3 / minio path


class Volume(Base, TenantMixin, TimestampMixin):
    __tablename__ = "volumes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: gen_id("vol"))
    compute_id: Mapped[str] = mapped_column(ForeignKey("computes.id"), nullable=False)
    size_gb: Mapped[int] = mapped_column(Integer, default=10)


# ---------- API Key / 用量 / 计费 ----------

class ApiKey(Base, TenantMixin, TimestampMixin):
    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: gen_id("key"))
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Usage(Base, TenantMixin, TimestampMixin):
    __tablename__ = "usage"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: gen_id("use"))
    compute_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metric: Mapped[str] = mapped_column(String(32), nullable=False)  # cpu_hours / storage_gb / transfer_gb
    amount: Mapped[float] = mapped_column(Float, default=0.0)

"""CloudPG Control Plane 配置 (pydantic-settings)."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Control Plane 数据库 (与用户 PG 完全分离)
    control_plane_dsn: str = "postgresql://cloudpg:cloudpg_secret@localhost:5433/cloudpg_cp"

    # 运行 PG 二进制与数据根
    pg_bin: str = "/usr/pgsql/bin"
    pg_version: str = "18"
    data_root: str = "/var/lib/cloudpg/instances"
    base_port: int = 5432

    # 连接入口 (PgBouncer / Envoy)
    pgbouncer_host: str = "localhost"
    pgbouncer_port: int = 6432
    external_host: str = "db.cloudpg.local"

    # 计算规格档位 (vCPU)
    compute_tiers: list[float] = [0.25, 0.5, 1.0, 2.0, 4.0]

    # 存储档位 (GB)
    storage_tiers: list[int] = [10, 50, 100, 500, 1024]

    # 自动挂起空闲阈值 (秒)
    idle_suspend_seconds: int = 300

    # JWT / API Key
    jwt_secret: str = "change-me-in-prod"
    jwt_algorithm: str = "HS256"
    api_key_secret: str = "change-me-in-prod"

    # 对象存储 (备份归档)
    s3_endpoint: str = ""
    s3_bucket: str = "cloudpg-backups"
    s3_access_key: str = ""
    s3_secret_key: str = ""


settings = Settings()

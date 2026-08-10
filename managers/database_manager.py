"""Database Manager — 在指定 Compute 实例上建库 / 删库 / 列表。

通过 psql 直连该实例的 PostgreSQL。
"""
from __future__ import annotations

import os
import subprocess

from apps.api.config import settings
from managers.compute_manager import _data_dir, _port_for, _run


def _psql(instance_id: str, db: str, sql: str) -> str:
    pg_bin = settings.pg_bin
    port = _port_for(instance_id)
    r = _run("postgres", [f"{pg_bin}/psql", "-h", "localhost", "-p", str(port), "-U", "cloudpg", "-d", db, "-t", "-A", "-c", sql])
    return r.stdout.strip()


def create_database(instance_id: str, name: str) -> None:
    _psql(instance_id, "postgres", f"CREATE DATABASE \"{name}\";")


def drop_database(instance_id: str, name: str) -> None:
    # 先终止连接再删除
    _psql(instance_id, "postgres",
          f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='{name}' AND pid<>pg_backend_pid();")
    _psql(instance_id, "postgres", f"DROP DATABASE IF EXISTS \"{name}\";")


def list_databases(instance_id: str) -> list[str]:
    out = _psql(instance_id, "postgres",
               "SELECT datname FROM pg_database WHERE datistemplate=false AND datname<>'postgres';")
    return [d for d in out.splitlines() if d] if out else []


def create_role(instance_id: str, name: str, password: str, readonly: bool = False) -> None:
    _psql(instance_id, "postgres", f"CREATE ROLE \"{name}\" LOGIN PASSWORD '{password}';")
    _psql(instance_id, "postgres", f"GRANT CONNECT ON DATABASE postgres TO \"{name}\";")
    if readonly:
        _psql(instance_id, "postgres", f"ALTER ROLE \"{name}\" SET default_transaction_read_only = on;")


def run_query(instance_id: str, database: str, sql: str) -> list[dict]:
    """简易查询执行 (用于 API /query 与 SQL Editor)。"""
    pg_bin = settings.pg_bin
    port = _port_for(instance_id)
    r = _run("postgres", [f"{pg_bin}/psql", "-h", "localhost", "-p", str(port), "-U", "cloudpg", "-d", database, "-X", "-F", ",", "--pset", "format=unaligned", "-c", sql])
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip())
    lines = [l for l in r.stdout.splitlines() if l]
    return [{"row": l} for l in lines]


def list_tables(instance_id: str, database: str) -> list[str]:
    """列出数据库中的用户表 (schema.table)。"""
    sql = (
        "SELECT format('%s.%s', table_schema, table_name) FROM information_schema.tables "
        "WHERE table_schema NOT IN ('pg_catalog','information_schema') AND table_type='BASE TABLE' "
        "ORDER BY table_schema, table_name;"
    )
    out = _psql(instance_id, database, sql)
    if not out:
        return []
    tables = []
    for line in out.splitlines():
        line = line.strip()
        if not line or "Time:" in line or line.startswith("(") or "rows" in line:
            continue
        tables.append(line)
    return tables


def read_logfile(instance_id: str, tail: int = 200) -> str:
    """读取 PG 实例日志 (data_dir/logfile)。"""
    log_path = os.path.join(_data_dir(instance_id), "logfile")
    if not os.path.exists(log_path):
        return ""
    try:
        r = subprocess.run(
            ["sudo", "-u", "postgres", "tail", "-n", str(tail), log_path],
            capture_output=True, text=True, check=False, timeout=5,
        )
        return r.stdout
    except Exception:  # noqa: BLE001
        return ""


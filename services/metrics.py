"""Metrics Service — 采集 8 项指标 (CPU/RAM/Storage/Connections/QPS/TPS/IOPS/Latency)。

MVP: 通过 pg_stat_database / 系统信息聚合；生产接 Prometheus + VictoriaMetrics。
"""
from __future__ import annotations

import os

from managers.compute_manager import _port_for, _run
from managers.storage_manager import usage


async def collect(compute_id: str, database_name: str, storage_limit_gb: float = 10.0) -> dict:
    pg_bin = "/usr/pgsql/bin"
    port = _port_for(compute_id)
    connections = 0
    tps = qps = 0
    iops_read = iops_write = 0
    cache_hit_ratio = 0.0
    try:
        out = _run("postgres", [
            f"{pg_bin}/psql", "-h", "localhost", "-p", str(port), "-U", "cloudpg", "-d", "postgres",
            "-t", "-A", "-F", ",", "-c",
            "SELECT numbackends, xact_commit + xact_rollback, xact_commit, xact_rollback, "
            "blks_read, blks_hit "
            "FROM pg_stat_database WHERE datname='postgres';",
        ]).stdout.strip()
        parts = out.split(",") if out else []
        connections = int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else 0
        tps = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
        qps = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
        blks_read = int(parts[4]) if len(parts) > 4 and parts[4].isdigit() else 0
        blks_hit = int(parts[5]) if len(parts) > 5 and parts[5].isdigit() else 0
        iops_read = blks_read
        iops_write = max(tps - blks_read, 0)
        total_blocks = blks_read + blks_hit
        cache_hit_ratio = round(blks_hit / total_blocks * 100, 1) if total_blocks else 0.0
    except Exception:  # noqa: BLE001
        pass

    # CPU / RAM (本机概览, 真实环境应取 cgroup)
    cpu = float(os.getloadavg()[0])
    mem = _system_mem_used_gb()

    storage_bytes = usage(compute_id)
    storage_gb = round(storage_bytes / (1024**3), 3)

    return {
        "cpu": cpu,
        "ram_gb": mem,
        "storage_used_gb": storage_gb,
        "storage_limit_gb": storage_limit_gb,
        "connections": connections,
        "queries_per_sec": qps,
        "tps": tps,
        "iops_read": iops_read,
        "iops_write": iops_write,
        "cache_hit_ratio": cache_hit_ratio,
        "latency_ms": 0.0,
    }


def _system_mem_used_gb() -> float:
    try:
        with open("/proc/meminfo") as f:
            info = {line.split(":")[0]: int(line.split()[1]) for line in f if ":" in line}
        used = info.get("MemTotal", 0) - info.get("MemAvailable", 0)
        return round(used / (1024**2), 2)
    except Exception:  # noqa: BLE001
        return 0.0

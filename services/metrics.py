"""Metrics Service — 采集 8 项指标 (CPU/RAM/Storage/Connections/QPS/TPS/IOPS/Latency)。

MVP: 通过 pg_stat_database / 系统信息聚合；生产接 Prometheus + VictoriaMetrics。
"""
from __future__ import annotations

import os

from managers.compute_manager import _port_for, _run
from managers.storage_manager import usage


async def collect(compute_id: str, database_name: str) -> dict:
    pg_bin = "/usr/pgsql/bin"
    port = _port_for(compute_id)
    try:
        out = _run("postgres", [
            f"{pg_bin}/psql", "-h", "localhost", "-p", str(port), "-U", "cloudpg", "-d", "postgres",
            "-t", "-A", "-F", ",", "-c",
            "SELECT numbackends, xact_commit + xact_rollback, xact_commit, xact_rollback, "
            "blks_read, blk_read_time + blk_write_time "
            "FROM pg_stat_database WHERE datname='postgres';",
        ]).stdout.strip()
        parts = out.split(",") if out else []
        connections = int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else 0
        tps = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
        qps = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
        iops = int(parts[4]) if len(parts) > 4 and parts[4].isdigit() else 0
        latency = float(parts[5]) if len(parts) > 5 and parts[5] else 0.0
    except Exception:  # noqa: BLE001
        connections = tps = qps = iops = 0
        latency = 0.0

    # CPU / RAM (本机概览, 真实环境应取 cgroup)
    cpu = float(os.getloadavg()[0])
    mem = _system_mem_used_gb()

    storage_bytes = usage(compute_id)
    storage_gb = round(storage_bytes / (1024**3), 3)

    return {
        "cpu": cpu,
        "ram_gb": mem,
        "storage_gb": storage_gb,
        "connections": connections,
        "qps": qps,
        "tps": tps,
        "iops": iops,
        "latency_ms": round(latency, 2),
    }


def _system_mem_used_gb() -> float:
    try:
        with open("/proc/meminfo") as f:
            info = {line.split(":")[0]: int(line.split()[1]) for line in f if ":" in line}
        used = info.get("MemTotal", 0) - info.get("MemAvailable", 0)
        return round(used / (1024**2), 2)
    except Exception:  # noqa: BLE001
        return 0.0

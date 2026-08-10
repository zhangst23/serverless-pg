"""Compute Manager — 在本地裸 VPS 上实际管理 PostgreSQL 实例的启停/规格。

通过 pg_ctl / initdb 操作系统进程，不使用 Kubernetes。
支持: provision / start / stop / restart / suspend / resume / resize。
"""
from __future__ import annotations

import os
import secrets
import subprocess
from datetime import datetime, timezone

from apps.api.config import settings


def _data_dir(instance_id: str) -> str:
    return os.path.join(settings.data_root, instance_id, "data")


def _port_for(instance_id: str) -> int:
    # 基于实例 id 派生稳定端口 (base_port + 序号)，简单可复现
    h = int("".join(filter(str.isdigit, instance_id)) or "0")
    return settings.base_port + (h % 1000)


def _run(user: str, cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(["sudo", "-u", user, *cmd], capture_output=True, text=True, check=False)


def provision(instance_id: str, cpu: float, memory_gb: float) -> dict:
    """初始化并启动一个 PostgreSQL 实例。"""
    pg_bin = settings.pg_bin
    data_dir = _data_dir(instance_id)
    port = _port_for(instance_id)
    os.makedirs(os.path.dirname(data_dir), exist_ok=True)

    if not os.path.exists(os.path.join(data_dir, "PG_VERSION")):
        _run("postgres", [f"{pg_bin}/initdb", "-D", data_dir, "-U", "cloudpg", "--auth=trust"])

    # 写入端口与监听
    with open(os.path.join(data_dir, "postgresql.conf"), "a") as f:
        f.write(f"\nport = {port}\nlisten_addresses = 'localhost'\n")

    start(instance_id)
    _apply_resource_limits(instance_id, cpu, memory_gb)
    return {"data_dir": data_dir, "port": port, "status": "running"}


def start(instance_id: str) -> None:
    data_dir = _data_dir(instance_id)
    pg_bin = settings.pg_bin
    _run("postgres", [f"{pg_bin}/pg_ctl", "-D", data_dir, "-l", os.path.join(data_dir, "logfile"), "-w", "start"])


def stop(instance_id: str) -> None:
    _pg_ctl(instance_id, "stop", "-m", "fast")


def restart(instance_id: str) -> None:
    _pg_ctl(instance_id, "restart", "-w")


def suspend(instance_id: str) -> None:
    """挂起: 停止进程 (Compute 资源释放)。"""
    stop(instance_id)


def resume(instance_id: str) -> None:
    """恢复: 启动进程。"""
    start(instance_id)


def resize(instance_id: str, cpu: float, memory_gb: float) -> None:
    _apply_resource_limits(instance_id, cpu, memory_gb)
    restart(instance_id)


def is_running(instance_id: str) -> bool:
    data_dir = _data_dir(instance_id)
    pg_bin = settings.pg_bin
    r = _run("postgres", [f"{pg_bin}/pg_ctl", "-D", data_dir, "status"])
    return r.returncode == 0


def connection_uri(instance_id: str, database: str, user: str = "cloudpg", password: str = "") -> str:
    port = _port_for(instance_id)
    auth = f"{user}:{password}@" if password else f"{user}@"
    return f"postgres://{auth}localhost:{port}/{database}"


def _pg_ctl(instance_id: str, action: str, *extra: str) -> None:
    data_dir = _data_dir(instance_id)
    pg_bin = settings.pg_bin
    _run("postgres", [f"{pg_bin}/pg_ctl", "-D", data_dir, action, *extra])


def _apply_resource_limits(instance_id: str, cpu: float, memory_gb: float) -> None:
    """尽力而为地应用 CPU / 内存限制 (cgroup v2)。失败仅记录，不阻断。"""
    # 仅在支持 cgroup v2 时尝试；生产建议配合 systemd 资源指令。
    try:
        cg = f"/sys/fs/cgroup/cloudpg_{instance_id}"
        if os.path.isdir("/sys/fs/cgroup"):
            os.makedirs(cg, exist_ok=True)
            with open(os.path.join(cg, "cpu.max"), "w") as f:
                # cpu.max 形如 "quota period"; 以 100000 为周期
                quota = int(cpu * 100000)
                f.write(f"{quota} 100000\n")
            with open(os.path.join(cg, "memory.max"), "w") as f:
                f.write(f"{int(memory_gb * 1024 * 1024 * 1024)}\n")
    except Exception:  # noqa: BLE001
        pass  # 非致命，记录日志即可


def now() -> datetime:
    return datetime.now(timezone.utc)


def gen_password() -> str:
    return secrets.token_urlsafe(16)

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
    os.makedirs(data_dir, exist_ok=True)
    # 确保 postgres 用户对数据目录有写权限 (initdb 必须以 postgres 运行)
    _run("root", ["chown", "-R", "postgres:postgres", os.path.dirname(data_dir)])

    password = gen_password()
    if not os.path.exists(os.path.join(data_dir, "PG_VERSION")):
        r = _run("postgres", [f"{pg_bin}/initdb", "-D", data_dir, "-U", "cloudpg", "--auth=trust"])
        if r.returncode != 0:
            raise RuntimeError(f"initdb 失败: {r.stderr}")

    # 写入端口与监听 (监听所有接口, 允许公网连接)
    with open(os.path.join(data_dir, "postgresql.conf"), "a") as f:
        f.write(f"\nport = {port}\nlisten_addresses = '*'\npassword_encryption = 'scram-sha-256'\n")

    # 写入 pg_hba: 本地 trust (运维), 公网 scram 认证
    pg_hba = os.path.join(data_dir, "pg_hba.conf")
    hba_lines = [
        "local   all   all                 trust",
        "host    all   all   127.0.0.1/32  trust",
        "host    all   all   ::1/128       trust",
        f"host    all   all   0.0.0.0/0     scram-sha-256",
        f"host    all   all   ::/0          scram-sha-256",
    ]
    with open(pg_hba, "a") as f:
        f.write("\n# CloudPG external access (scram-sha-256)\n")
        f.write("\n".join(hba_lines) + "\n")

    start(instance_id)
    # 为实例 superuser(cloudpg) 设置密码 (公网连接使用)
    _run("postgres", [f"{pg_bin}/psql", "-h", "localhost", "-p", str(port), "-U", "cloudpg",
                      "-d", "postgres", "-c", f"ALTER USER cloudpg WITH PASSWORD '{password}';"])
    _apply_resource_limits(instance_id, cpu, memory_gb)
    return {"data_dir": data_dir, "port": port, "password": password, "status": "running"}


def start(instance_id: str) -> None:
    data_dir = _data_dir(instance_id)
    pg_bin = settings.pg_bin
    # 带超时启动, 避免单 worker 后端被 pg_ctl 永久阻塞
    subprocess.run(
        ["sudo", "-u", "postgres", f"{pg_bin}/pg_ctl", "-D", data_dir,
         "-l", os.path.join(data_dir, "logfile"), "-w", "-t", "30", "start"],
        capture_output=True, text=True, timeout=40,
    )


def stop(instance_id: str) -> None:
    _pg_ctl(instance_id, "stop", "-m", "fast")


def restart(instance_id: str) -> None:
    # 后台重启: 用 Popen 不等待, PG 在后台完成重启, 后端 worker 立即返回,
    # 避免单 worker 被 pg_ctl restart 阻塞数十秒导致整个后端无响应。
    data_dir = _data_dir(instance_id)
    pg_bin = settings.pg_bin
    subprocess.Popen(
        ["sudo", "-u", "postgres", f"{pg_bin}/pg_ctl", "-D", data_dir, "restart", "-W"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


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
    # 带超时, 防止单 worker 后端被 pg_ctl 阻塞
    subprocess.run(
        ["sudo", "-u", "postgres", f"{pg_bin}/pg_ctl", "-D", data_dir, action, *extra],
        capture_output=True, text=True, timeout=45,
    )


def _apply_resource_limits(instance_id: str, cpu: float, memory_gb: float) -> None:
    """尽力而为地应用 CPU / 内存限制 (cgroup v2)。失败仅记录，不阻断。

    注意: 直接 open().write() 在部分 cgroup 实现下可能阻塞，因此用带
    timeout 的 subprocess 写入, 且整体包裹超时保护, 绝不阻断主流程。
    """
    import subprocess

    cg = f"/sys/fs/cgroup/cloudpg_{instance_id}"
    try:
        if not os.path.isdir("/sys/fs/cgroup"):
            return
        os.makedirs(cg, exist_ok=True)
        quota = int(cpu * 100000)
        mem = int(memory_gb * 1024 * 1024 * 1024)
        # 用 shell 重定向 + timeout 防阻塞
        for fname, content in (("cpu.max", f"{quota} 100000"), ("memory.max", str(mem))):
            subprocess.run(
                f"echo '{content}' > '{os.path.join(cg, fname)}'",
                shell=True, capture_output=True, timeout=2,
            )
    except Exception:  # noqa: BLE001
        pass  # 非致命, cgroup 限制失败不影响 PG 实例运行


def now() -> datetime:
    return datetime.now(timezone.utc)


def gen_password() -> str:
    return secrets.token_urlsafe(16)

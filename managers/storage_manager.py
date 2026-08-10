"""Storage Manager — 容量配额、挂载点、数据目录布局。

MVP: 本地 NVMe/SSD 目录 + 档位映射。归档到 S3/MinIO 由 Backup 负责。
"""
from __future__ import annotations

import os

from apps.api.config import settings

STORAGE_TIERS = [10, 50, 100, 500, 1024]


def validate_tier(size_gb: int) -> int:
    if size_gb not in STORAGE_TIERS:
        raise ValueError(f"非法存储档位 {size_gb}，可选: {STORAGE_TIERS}")
    return size_gb


def allocate(instance_id: str, size_gb: int) -> str:
    """为实例分配数据目录 (容量配额由文件系统/后续 cgroup 增强)。"""
    validate_tier(size_gb)
    path = os.path.join(settings.data_root, instance_id, "data")
    os.makedirs(path, exist_ok=True)
    return path


def usage(instance_id: str) -> int:
    """返回实例当前数据目录已用字节数。"""
    data_dir = os.path.join(settings.data_root, instance_id, "data")
    total = 0
    for root, _dirs, files in os.walk(data_dir):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total

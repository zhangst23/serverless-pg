"""CloudPG Python SDK — typed 客户端 (连接/查询/角色/启停 Compute)。"""
from __future__ import annotations

import os
from typing import Any

try:
    import httpx
except ImportError:  # pragma: no cover
    httpx = None


class CloudPGError(RuntimeError):
    pass


class CloudPG:
    def __init__(self, api_key: str | None = None, base_url: str | None = None, project_id: str | None = None):
        if httpx is None:
            raise CloudPGError("请先安装 httpx: pip install httpx")
        self.base_url = (base_url or os.environ.get("CLOUDPG_API", "http://localhost:8000")).rstrip("/")
        self.api_key = api_key or os.environ.get("CLOUDPG_API_KEY", "")
        self.project_id = project_id or os.environ.get("CLOUDPG_PROJECT_ID", "")
        if not self.api_key:
            raise CloudPGError("缺少 API Key (CLOUDPG_API_KEY)")

    def _headers(self) -> dict:
        return {"X-API-Key": self.api_key, "Content-Type": "application/json"}

    def _call(self, method: str, path: str, body: dict | None = None) -> Any:
        r = httpx.request(method, f"{self.base_url}{path}", headers=self._headers(), json=body, timeout=30)
        if r.status_code >= 400:
            raise CloudPGError(f"{r.status_code}: {r.text}")
        return r.json()

    # --- 资源 ---
    def create_database(self, name: str, cpu: float = 1.0) -> dict:
        return self._call("POST", "/api/v1/databases", {"name": name, "cpu": cpu})

    def list_databases(self) -> list[dict]:
        return self._call("GET", "/api/v1/databases")

    def delete_database(self, database_id: str) -> dict:
        return self._call("DELETE", f"/api/v1/databases/{database_id}")

    def query(self, database_id: str, sql: str) -> dict:
        return self._call("POST", f"/api/v1/databases/{database_id}/query", {"sql": sql})

    def compute_action(self, compute_id: str, action: str) -> dict:
        return self._call("POST", f"/api/v1/computes/{compute_id}/{action}")

    def resize_compute(self, compute_id: str, cpu: float) -> dict:
        return self._call("PATCH", f"/api/v1/computes/{compute_id}", {"cpu": cpu})

    def create_backup(self, database_id: str) -> dict:
        return self._call("POST", "/api/v1/backups", {"database_id": database_id})

    def create_role(self, name: str, privilege: str = "readwrite") -> dict:
        return self._call("POST", f"/api/v1/projects/{self.project_id}/roles", {"name": name, "privilege": privilege})

    def connection_string(self) -> dict:
        return self._call("GET", f"/api/v1/projects/{self.project_id}/connection-string")

    def metrics(self, database_id: str) -> dict:
        return self._call("GET", f"/api/v1/metrics/databases/{database_id}")

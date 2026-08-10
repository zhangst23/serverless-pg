"""冒烟测试: 不依赖真实 PG 进程，验证应用加载与纯逻辑。

运行: 在 venv 中  pytest apps/api/test_smoke.py
(或) python -m apps.api.test_smoke
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi.testclient import TestClient  # type: ignore

from apps.api.main import app
from managers import compute_manager as cm
from services import compute as compute_svc
from apps.api.routers import roles as roles_router


def test_app_loads():
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_routes_registered():
    paths = set(app.openapi()["paths"].keys())
    for p in ["/api/v1/projects", "/api/v1/databases", "/api/v1/computes/{compute_id}/start",
              "/api/v1/backups", "/api/v1/metrics/databases/{database_id}",
              "/api/v1/projects/{project_id}/roles"]:
        assert p in paths, f"missing route {p}"


def test_port_derivation_stable():
    a = cm._port_for("comp_abc123")
    b = cm._port_for("comp_abc123")
    assert a == b
    assert 5432 <= a < 6432


def test_cpu_mem_mapping():
    for cpu in [0.25, 0.5, 1.0, 2.0, 4.0]:
        assert cpu in compute_svc.CPU_MEM
    assert compute_svc.CPU_MEM[0.25] == 0.5
    assert compute_svc.CPU_MEM[4.0] == 8.0


def test_connection_string_snippets():
    snips = roles_router._snippets("mydb", "alice", "pw")
    assert snips["connection_string"].startswith("postgres://alice:pw@")
    assert "DATABASE_URL" in snips["env"]
    assert "psycopg" in snips["python"]


if __name__ == "__main__":
    test_app_loads()
    test_routes_registered()
    test_port_derivation_stable()
    test_cpu_mem_mapping()
    test_connection_string_snippets()
    print("ALL SMOKE TESTS PASSED")

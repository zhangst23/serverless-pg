#!/usr/bin/env python3
"""cloudpg CLI — 开发者友好的 Serverless PostgreSQL 命令行。

子命令:
  cloudpg login                配置 API Key
  cloudpg projects             列出项目
  cloudpg db create <name>     创建数据库 (含 Compute + Endpoint)
  cloudpg db list              列出数据库
  cloudpg db delete <id>       删除数据库
  cloudpg sql <db_id> <sql>    执行 SQL
  cloudpg db connect <db_id>   一键直连 (psql)
  cloudpg db dump <db_id>      导出 (pg_dump)
  cloudpg db restore <db_id> <file>  导入
  cloudpg logs <db_id>         查看 PG 日志
  cloudpg warm <db_id>         保活/预热
  cloudpg compute start|stop|restart|suspend|resume|resize

环境变量: CLOUDPG_API (默认 http://localhost:8000) CLOUDPG_API_KEY
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

API = os.environ.get("CLOUDPG_API", "http://localhost:8000")
KEY = os.environ.get("CLOUDPG_API_KEY", "")
CONFIG_PATH = os.path.expanduser("~/.cloudpg/config.json")


def _headers() -> dict:
    return {"X-API-Key": KEY or _load_key()}


def _load_key() -> str:
    try:
        with open(CONFIG_PATH) as f:
            return json.load(f).get("api_key", "")
    except Exception:  # noqa: BLE001
        return ""


def _req(method: str, path: str, body: dict | None = None) -> dict:
    import urllib.request

    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{API}{path}", data=data, headers=_headers(), method=method)
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        sys.stderr.write(f"HTTP {e.code}: {e.read().decode()}\n")
        sys.exit(1)


def cmd_login(args: argparse.Namespace) -> None:
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump({"api_key": args.api_key}, f)
    print(f"已保存 API Key 到 {CONFIG_PATH}")


def cmd_projects(_: argparse.Namespace) -> None:
    for p in _req("GET", "/api/v1/projects"):
        print(f"{p['id']}  {p['name']}  region={p['region']}")


def cmd_db_create(args: argparse.Namespace) -> None:
    res = _req("POST", "/api/v1/databases", {"name": args.name, "cpu": args.cpu})
    print(json.dumps(res, indent=2))


def cmd_db_list(_: argparse.Namespace) -> None:
    for d in _req("GET", "/api/v1/databases"):
        print(f"{d['id']}  {d['name']}  {d['status']}")


def cmd_db_delete(args: argparse.Namespace) -> None:
    print(json.dumps(_req("DELETE", f"/api/v1/databases/{args.id}"), indent=2))


def cmd_sql(args: argparse.Namespace) -> None:
    res = _req("POST", f"/api/v1/databases/{args.db_id}/query", {"sql": args.sql})
    for row in res.get("rows", []):
        print(row)


def cmd_compute(args: argparse.Namespace) -> None:
    action = args.action
    if action == "resize":
        res = _req("PATCH", f"/api/v1/computes/{args.id}", {"cpu": args.cpu})
    else:
        res = _req("POST", f"/api/v1/computes/{args.id}/{action}")
    print(json.dumps(res, indent=2))


def _endpoint_conn(args: argparse.Namespace) -> str:
    # 取 database 的 endpoint 连接串
    dbs = _req("GET", "/api/v1/databases")
    target = next((d for d in dbs if d["id"] == args.db_id), None)
    if not target:
        sys.stderr.write("db not found\n")
        sys.exit(1)
    # 简化: 直接用连接串接口
    cs = _req("GET", f"/api/v1/projects/{target.get('project_id','')}/connection-string")
    return cs.get("connection_string", "")


def cmd_connect(args: argparse.Namespace) -> None:
    cs = _endpoint_conn(args)
    subprocess.run(["psql", cs])


def cmd_dump(args: argparse.Namespace) -> None:
    cs = _endpoint_conn(args)
    subprocess.run(["pg_dump", cs, "-f", args.file])


def cmd_restore(args: argparse.Namespace) -> None:
    cs = _endpoint_conn(args)
    subprocess.run(["psql", cs, "-f", args.file])


def cmd_logs(args: argparse.Namespace) -> None:
    dbs = _req("GET", "/api/v1/databases")
    target = next((d for d in dbs if d["id"] == args.db_id), None)
    if not target or not target.get("compute_id"):
        sys.stderr.write("db not found\n")
        sys.exit(1)
    log = f"/var/lib/cloudpg/instances/{target['compute_id']}/data/logfile"
    subprocess.run(["tail", "-n", str(args.n), log])


def cmd_warm(args: argparse.Namespace) -> None:
    # 触发一次查询以唤醒 (Resume)
    res = _req("POST", f"/api/v1/databases/{args.db_id}/query", {"sql": "SELECT 1;"})
    print("warm ok:", res.get("rows"))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="cloudpg", description="CloudPG CLI")
    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("login").add_argument("api_key")
    sub.add_parser("projects")

    pd = sub.add_parser("db")
    pd_sub = pd.add_subparsers(dest="db_cmd")
    c = pd_sub.add_parser("create"); c.add_argument("name"); c.add_argument("--cpu", type=float, default=1.0)
    pd_sub.add_parser("list")
    dl = pd_sub.add_parser("delete"); dl.add_argument("id")
    ps = pd_sub.add_parser("sql"); ps.add_argument("db_id"); ps.add_argument("sql")
    pc = pd_sub.add_parser("connect"); pc.add_argument("db_id")
    pdmp = pd_sub.add_parser("dump"); pdmp.add_argument("db_id"); pdmp.add_argument("file")
    pr = pd_sub.add_parser("restore"); pr.add_argument("db_id"); pr.add_argument("file")

    pl = sub.add_parser("logs"); pl.add_argument("db_id"); pl.add_argument("-n", type=int, default=50)
    pw = sub.add_parser("warm"); pw.add_argument("db_id")

    pc2 = sub.add_parser("compute"); pc2.add_argument("action", choices=["start", "stop", "restart", "suspend", "resume", "resize"])
    pc2.add_argument("id"); pc2.add_argument("--cpu", type=float, default=1.0)
    return p


DISPATCH = {
    "login": cmd_login, "projects": cmd_projects,
    "db": {"create": cmd_db_create, "list": cmd_db_list, "delete": cmd_db_delete, "sql": cmd_sql,
           "connect": cmd_connect, "dump": cmd_dump, "restore": cmd_restore},
    "logs": cmd_logs, "warm": cmd_warm,
    "compute": cmd_compute,
}


def main() -> None:
    args = build_parser().parse_args()
    if args.cmd == "db":
        DISPATCH["db"][args.db_cmd](args)
    elif args.cmd in DISPATCH:
        DISPATCH[args.cmd](args)
    else:
        build_parser().print_help()


if __name__ == "__main__":
    main()

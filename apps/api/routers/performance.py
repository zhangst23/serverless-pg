"""PG 性能路由 — 管理提升 PostgreSQL 性能的扩展(插件)与运行参数。

所有操作都针对某个具体 database（通过其所属 compute 实例执行）。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from apps.api.deps import get_db
from apps.api.security import AuthContext, require_auth
from db.session import AsyncSession
from managers.database_manager import run_command, run_query_json
from services import database as db_svc
from services import compute as compute_svc

router = APIRouter(prefix="/performance", tags=["performance"])

# 允许通过本接口设置的性能参数白名单 (GUC)。
# 仅暴露对性能影响明显且可安全调整的参数，避免误改关键安全/复制参数。
ALLOWED_SETTINGS = {
    "shared_buffers",
    "work_mem",
    "maintenance_work_mem",
    "effective_cache_size",
    "max_connections",
    "random_page_cost",
    "seq_page_cost",
    "default_statistics_target",
    "wal_buffers",
    "checkpoint_completion_target",
    "effective_io_concurrency",
    "temp_file_limit",
    "statement_timeout",
    "lock_timeout",
    "idle_in_transaction_session_timeout",
    "max_parallel_workers_per_gather",
    "max_parallel_workers",
    "max_parallel_maintenance_workers",
    "jit",
    "synchronous_commit",
}

# 常见提升性能的扩展说明 (name -> 简介)
EXTENSION_INFO = {
    "pg_stat_statements": "跟踪 SQL 执行统计，定位慢查询与热点语句。",
    "pg_buffercache": "查看共享缓冲区的使用情况，辅助调优 shared_buffers。",
    "pgstattuple": "分析表/索引的空闲空间与膨胀情况。",
    "auto_explain": "自动记录慢查询的执行计划。",
    "pgcrypto": "提供哈希与加密函数，支持数据落盘加密。",
    "postgres_fdw": "跨库联邦查询，将远程表映射为本地外部表。",
    "pg_partman": "为时间序列等大表提供原生分区表自动维护。",
    "btree_gin": "为 GIN 索引提供 btree 算子支持，加速多列组合查询。",
    "btree_gist": "为 GiST 索引提供 btree 算子支持，支持排他约束。",
    "pg_trgm": "trigram 相似度匹配，加速 LIKE / 模糊搜索与全文检索。",
    "hstore": "键值对数据类型，适合半结构化数据。",
    "citext": "大小写不敏感的文本类型。",
    "uuid-ossp": "生成 UUID 的函数。",
    "tablefunc": "提供 crosstab 等交叉表函数。",
    "intarray": "整数数组的索引与操作符，加速标签/集合查询。",
    "dict_int": "整型全文检索词典。",
    "unaccent": "全文检索中去音标的文本搜索词典。",
    "pg_hint_plan": "通过 SQL 注释下发查询提示(hint)以干预执行计划。",
    "hypopg": "虚拟索引，无需真正创建即可评估索引收益。",
    "pg_prewarm": "将表/索引预热进缓冲区，减少冷启动抖动。",
    "pageinspect": "底层页检查工具，用于诊断与性能分析。",
    "amcheck": "校验索引逻辑一致性，预防数据损坏导致的性能退化。",
}


class ExtensionInstall(BaseModel):
    name: str
    database_id: str
    target_schema: str | None = None


class ExtensionDrop(BaseModel):
    database_id: str


class SettingSet(BaseModel):
    name: str
    value: str
    database_id: str
    # 应用级别: 数据库级 (ALTER DATABASE) 或实例级 (ALTER SYSTEM)
    scope: str = "database"  # database | system


@router.get("/extensions", response_model=dict)
async def list_extensions(
    database_id: str,
    auth: AuthContext = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """列出指定数据库已安装与可用的扩展。"""
    d = await db_svc.get(db, database_id)
    if not d or not d.compute_id:
        raise HTTPException(status_code=404, detail="not found")
    if d.status == "suspended" and d.compute_id:
        await compute_svc.resume_compute(
            db, compute_id=d.compute_id,
            organization_id=auth.organization_id, project_id=auth.project_id,
        )

    # 已安装扩展
    installed_sql = (
        "SELECT e.extname AS name, n.nspname AS schema, "
        "e.extversion AS version, d.description AS comment "
        "FROM pg_extension e "
        "LEFT JOIN pg_namespace n ON n.oid = e.extnamespace "
        "LEFT JOIN pg_description d ON d.objoid = e.oid AND d.classoid = 'pg_extension'::regclass "
        "ORDER BY e.extname"
    )
    installed = run_query_json(d.compute_id, d.name, installed_sql)
    installed_names = {row.get("name") for row in installed}

    # 可用扩展
    available_sql = (
        "SELECT name, default_version AS version, comment "
        "FROM pg_available_extensions ORDER BY name"
    )
    available = run_query_json(d.compute_id, d.name, available_sql)

    extras = []
    for row in available:
        name = row.get("name")
        extras.append({
            "name": name,
            "version": row.get("version"),
            "comment": row.get("comment") or EXTENSION_INFO.get(name, ""),
            "installed": name in installed_names,
            "installed_version": next(
                (i.get("version") for i in installed if i.get("name") == name), None
            ),
        })

    return {"installed": installed, "available": extras}


@router.post("/extensions", response_model=dict)
async def install_extension(
    body: ExtensionInstall,
    auth: AuthContext = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    d = await db_svc.get(db, database_id=body.database_id)
    if not d or not d.compute_id:
        raise HTTPException(status_code=404, detail="not found")
    name = body.name.strip()
    if not name or not name.replace("_", "").isalnum():
        raise HTTPException(status_code=400, detail="非法的扩展名")
    target = body.target_schema.strip() if body.target_schema else None
    sql = f'CREATE EXTENSION IF NOT EXISTS "{name}"'
    if target:
        sql += f' SCHEMA "{target}"'
    try:
        run_command(d.compute_id, d.name, sql)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"installed": name}


@router.delete("/extensions/{name}", response_model=dict)
async def drop_extension(
    name: str,
    body: ExtensionDrop,
    auth: AuthContext = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    d = await db_svc.get(db, database_id=body.database_id)
    if not d or not d.compute_id:
        raise HTTPException(status_code=404, detail="not found")
    safe_name = name.strip()
    if not safe_name or not safe_name.replace("_", "").isalnum():
        raise HTTPException(status_code=400, detail="非法的扩展名")
    try:
        run_command(d.compute_id, d.name, f'DROP EXTENSION IF EXISTS "{safe_name}" CASCADE')
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"dropped": safe_name}


@router.get("/settings", response_model=dict)
async def list_settings(
    database_id: str,
    auth: AuthContext = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """列出性能相关运行参数 (当前值、单位、是否可设置)。"""
    d = await db_svc.get(db, database_id)
    if not d or not d.compute_id:
        raise HTTPException(status_code=404, detail="not found")
    if d.status == "suspended" and d.compute_id:
        await compute_svc.resume_compute(
            db, compute_id=d.compute_id,
            organization_id=auth.organization_id, project_id=auth.project_id,
        )
    names = list(ALLOWED_SETTINGS)
    placeholders = ", ".join(f"'{n}'" for n in names)
    sql = (
        "SELECT name, setting AS current_value, unit, vartype, "
        "short_desc AS description, "
        "CASE WHEN unit IS NULL THEN setting ELSE setting || ' ' || unit END AS display "
        "FROM pg_settings WHERE name IN (" + placeholders + ") ORDER BY name"
    )
    rows = run_query_json(d.compute_id, d.name, sql)
    return {"settings": rows}


@router.post("/settings", response_model=dict)
async def set_setting(
    body: SettingSet,
    auth: AuthContext = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    name = body.name.strip()
    if name not in ALLOWED_SETTINGS:
        raise HTTPException(status_code=400, detail=f"不允许调整该参数: {name}")
    d = await db_svc.get(db, database_id=body.database_id)
    if not d or not d.compute_id:
        raise HTTPException(status_code=404, detail="not found")
    value = body.value.strip()
    if not value:
        raise HTTPException(status_code=400, detail="参数值不能为空")
    # 防注入: 仅允许安全字符 (字母/数字/下划线/点/空格/单位)
    if not all(c.isalnum() or c in ("_", ".", " ", "-", "%", "/", "B", "k", "M", "G", "T", "m", "s", "d") for c in value):
        raise HTTPException(status_code=400, detail="参数值包含非法字符")

    if body.scope == "system":
        sql = f'ALTER SYSTEM SET "{name}" = $${value}$$'
    else:
        sql = f'ALTER DATABASE "{d.name}" SET "{name}" = $${value}$$'
    try:
        run_command(d.compute_id, "postgres", sql)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"name": name, "value": value, "scope": body.scope}

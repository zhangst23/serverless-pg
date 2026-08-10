#!/usr/bin/env bash
#
# Phase 0 验证脚本: Create -> Connect -> Query -> Delete
# 在本地裸 VPS 上用一个临时 PostgreSQL 实例验证基础链路。
#
set -euo pipefail

PG_BIN="/usr/pgsql/bin"
TMP_DIR="$(mktemp -d)"
PORT=5444
DB="verify_db"
TABLE="t"

cleanup() { sudo -u postgres "${PG_BIN}/pg_ctl" -D "${TMP_DIR}" stop >/dev/null 2>&1 || true; rm -rf "${TMP_DIR}"; }
trap cleanup EXIT

echo "==> [verify] initdb"
sudo -u postgres "${PG_BIN}/initdb" -D "${TMP_DIR}" -U postgres --auth=trust >/dev/null

echo "==> [verify] start PG on port ${PORT}"
echo "port = ${PORT}" >> "${TMP_DIR}/postgresql.conf"
sudo -u postgres "${PG_BIN}/pg_ctl" -D "${TMP_DIR}" -l "${TMP_DIR}/log" start
sleep 2

echo "==> [Create] 建库 ${DB}"
sudo -u postgres "${PG_BIN}/psql" -p ${PORT} -c "CREATE DATABASE ${DB};" >/dev/null

echo "==> [Connect + Query] 建表/插入/查询"
sudo -u postgres "${PG_BIN}/psql" -p ${PORT} -d ${DB} -c "CREATE TABLE ${TABLE}(id int); INSERT INTO ${TABLE} VALUES (1),(2);" >/dev/null
OUT=$(sudo -u postgres "${PG_BIN}/psql" -p ${PORT} -d ${DB} -t -A -c "SELECT count(*) FROM ${TABLE};")
[ "${OUT}" = "2" ] && echo "    查询结果: count=${OUT}  OK"

echo "==> [Delete] 删库 ${DB}"
sudo -u postgres "${PG_BIN}/psql" -p ${PORT} -c "DROP DATABASE ${DB};" >/dev/null

echo "==> [verify] 停止并清理"
sudo -u postgres "${PG_BIN}/pg_ctl" -D "${TMP_DIR}" stop >/dev/null
rm -rf "${TMP_DIR}"

echo "==> Phase 0 验证通过: Create -> Connect -> Query -> Delete"

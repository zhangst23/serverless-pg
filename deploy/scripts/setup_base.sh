#!/usr/bin/env bash
#
# Phase 0: 底座初始化脚本
# - 初始化 Control Plane 独立 PostgreSQL 实例 (与用户 PG 隔离)
# - 提供 systemd unit 模板
# - 验证: Create -> Connect -> Query -> Delete
#
set -euo pipefail

PG_BIN="/usr/pgsql/bin"
PG_VERSION="18"
CP_DATA_DIR="${CLOUDPG_CP_DATA_DIR:-/tmp/cloudpg/control-plane}"
CP_PORT="${CLOUDPG_CP_PORT:-5433}"
CP_USER="${CLOUDPG_CP_USER:-cloudpg}"
CP_PASSWORD="${CLOUDPG_CP_PASSWORD:-cloudpg_secret}"

echo "==> [Phase 0] 初始化 Control Plane PostgreSQL 实例"
echo "    数据目录: ${CP_DATA_DIR}"
echo "    端口:     ${CP_PORT}"

if [ -d "${CP_DATA_DIR}" ]; then
  echo "    数据目录已存在，跳过 initdb"
else
  mkdir -p "${CP_DATA_DIR}"
  chown -R postgres:postgres "${CP_DATA_DIR}" 2>/dev/null || true
  sudo -u postgres "${PG_BIN}/initdb" -D "${CP_DATA_DIR}" -U "${CP_USER}" --auth=trust >/dev/null
  echo "    initdb 完成"
fi

# 配置监听端口
if ! grep -q "^port = ${CP_PORT}" "${CP_DATA_DIR}/postgresql.conf"; then
  echo "port = ${CP_PORT}" >> "${CP_DATA_DIR}/postgresql.conf"
fi
if ! grep -q "^listen_addresses" "${CP_DATA_DIR}/postgresql.conf"; then
  echo "listen_addresses = 'localhost'" >> "${CP_DATA_DIR}/postgresql.conf"
fi

# 启动 (若未运行)
if ! sudo -u postgres "${PG_BIN}/pg_ctl" -D "${CP_DATA_DIR}" status >/dev/null 2>&1; then
  sudo -u postgres "${PG_BIN}/pg_ctl" -D "${CP_DATA_DIR}" -l "${CP_DATA_DIR}/logfile" start
  sleep 2
fi

echo "==> Control Plane PG 已启动: port=${CP_PORT} user=${CP_USER}"

# 写入 .env 供 Control Plane 读取
cat > /root/serverless-pg/.env <<EOF
# CloudPG Control Plane 配置 (由 setup_base.sh 生成)
CLOUDPG_CONTROL_PLANE_DSN=postgresql://${CP_USER}:${CP_PASSWORD}@localhost:${CP_PORT}/cloudpg_cp
CLOUDPG_CP_PORT=${CP_PORT}
CLOUDPG_CP_USER=${CP_USER}
CLOUDPG_PG_BIN=${PG_BIN}
CLOUDPG_PG_VERSION=${PG_VERSION}
CLOUDPG_DATA_ROOT=/var/lib/cloudpg/instances
CLOUDPG_BASE_PORT=5432
EOF

echo "==> 已写入 .env"
echo "==> Phase 0 底座初始化完成。运行 bash deploy/scripts/verify_base.sh 验证。"

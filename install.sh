#!/usr/bin/env bash
#
# CloudPG 一键部署脚本
# ---------------------------------------------------------------
# 在裸 Ubuntu 24.04 VPS 上一键部署 CloudPG (Serverless PostgreSQL 平台):
#   - Control Plane (FastAPI)  监听 127.0.0.1:8000
#   - Web 控制台 (Next.js)     监听 127.0.0.1:3002
#   - Nginx 反代: / -> :3002, /api/ -> :8000
#   - Control Plane 独立 PostgreSQL 实例 (与用户 PG 隔离)
#
# 用法:
#   bash install.sh                         # 交互式: 自动检测依赖并部署当前目录
#   bash install.sh --source /path/to/repo  # 指定项目源码目录
#   bash install.sh --public-ip 1.2.3.4 \
#       --admin-email admin@example.com --admin-password 'StrongPass123' \
#       --org acme --org-name 'Acme Inc'
#
# 说明:
#   - 默认假设 PostgreSQL 18 已装在 /usr/pgsql/bin (PGDG 仓库);
#     若缺失，脚本会尝试自动安装 PGDG 仓库与 postgresql-18。
#   - 脚本尽量幂等: 已存在的数据目录 / 服务会被跳过或复用。
# ---------------------------------------------------------------
set -euo pipefail

# ====================== 配置 (可用环境变量 / 参数覆盖) ======================
PG_BIN="${CLOUDPG_PG_BIN:-/usr/pgsql/bin}"
PG_VERSION="${CLOUDPG_PG_VERSION:-18}"
CP_DATA_DIR="${CLOUDPG_CP_DATA_DIR:-/var/lib/cloudpg/control-plane}"
CP_PORT="${CLOUDPG_CP_PORT:-5433}"
CP_USER="${CLOUDPG_CP_USER:-cloudpg}"
CP_PASSWORD="${CLOUDPG_CP_PASSWORD:-$(openssl rand -hex 12 2>/dev/null || echo cloudpg_secret)}"

API_PORT=8000
WEB_PORT=3002
APP_USER="${CLOUDPG_APP_USER:-$(logname 2>/dev/null || whoami)}"
PROJECT_DIR="${CLOUDPG_SOURCE:-$(cd "$(dirname "$0")" && pwd)}"

ADMIN_EMAIL="${SEED_ADMIN_EMAIL:-admin@example.com}"
ADMIN_PASSWORD="${SEED_ADMIN_PASSWORD:-admin123456}"
SEED_ORG="${SEED_ORG:-acme}"
SEED_ORG_NAME="${SEED_ORG_NAME:-Acme Inc}"
PUBLIC_IP="${CLOUDPG_PUBLIC_IP:-$(curl -fsS --max-time 5 https://api.ipify.org 2>/dev/null || echo 127.0.0.1)}"

LOG_DIR="/var/log/cloudpg"
VENV_DIR="${PROJECT_DIR}/.venv"
SYSTEMD_API="/etc/systemd/system/cloudpg-api.service"
NGINX_CONF="/etc/nginx/conf.d/cloudpg.conf"

# ====================== 解析参数 ======================
while [ $# -gt 0 ]; do
  case "$1" in
    --source)        PROJECT_DIR="$2"; shift 2 ;;
    --public-ip)     PUBLIC_IP="$2"; shift 2 ;;
    --admin-email)   ADMIN_EMAIL="$2"; shift 2 ;;
    --admin-password) ADMIN_PASSWORD="$2"; shift 2 ;;
    --org)           SEED_ORG="$2"; shift 2 ;;
    --org-name)      SEED_ORG_NAME="$2"; shift 2 ;;
    --pg-bin)        PG_BIN="$2"; shift 2 ;;
    -h|--help)       sed -n '2,28p' "$0"; exit 0 ;;
    *) echo "未知参数: $1"; exit 1 ;;
  esac
done

# ====================== 工具函数 ======================
log()  { echo -e "\033[32m[CloudPG]\033[0m $*"; }
warn() { echo -e "\033[33m[WARN]\033[0m $*"; }
err()  { echo -e "\033[31m[ERROR]\033[0m $*"; exit 1; }
need_root() { [ "$(id -u)" -eq 0 ] || err "请使用 root 运行: sudo bash install.sh"; }

# 检测 systemd 可用性
HAS_SYSTEMD=0
if command -v systemctl >/dev/null 2>&1 && systemctl --no-pager status >/dev/null 2>&1; then
  HAS_SYSTEMD=1
fi

# ====================== 0. 前置检查 ======================
need_root
[ -d "${PROJECT_DIR}/apps/api" ] || err "项目目录无效，未找到 apps/api: ${PROJECT_DIR}"
cd "${PROJECT_DIR}"

# ====================== 1. 系统依赖 ======================
log "检测系统依赖…"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y -qq

# Python venv / pip
if ! python3 -m venv --help >/dev/null 2>&1; then
  apt-get install -y -qq python3-venv python3-pip
fi

# Nginx
if ! command -v nginx >/dev/null 2>&1; then
  apt-get install -y -qq nginx
fi

# Node.js 20 (若缺失或未达 18)
if ! command -v node >/dev/null 2>&1 || [ "$(node -v | cut -d. -f1 | tr -d v)" -lt 18 ]; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt-get install -y -qq nodejs
fi

# PostgreSQL 18 (优先检测 /usr/pgsql/bin, 其次 apt postgresql-18)
if [ -x "${PG_BIN}/postgres" ]; then
  log "PostgreSQL 二进制已存在: ${PG_BIN}"
else
  warn "未找到 ${PG_BIN}/postgres，尝试安装 PostgreSQL ${PG_VERSION} (PGDG)…"
  if ! ls /etc/apt/sources.list.d/pgdg.list >/dev/null 2>&1; then
    apt-get install -y -qq curl ca-certificates gnupg lsb-release
    install -d /usr/share/postgresql-common/pgdg
    curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc \
      | gpg --dearmor -o /usr/share/postgresql-common/pgdg/apt.gpg
    echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.gpg] https://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" \
      > /etc/apt/sources.list.d/pgdg.list
    apt-get update -y -qq
  fi
  apt-get install -y -qq "postgresql-${PG_VERSION}"
  # 兜底: 让 PG_BIN 指向发行版默认路径
  PG_BIN="$(ls -d /usr/lib/postgresql/${PG_VERSION}/bin 2>/dev/null || echo /usr/pgsql/bin)"
  log "已安装 PostgreSQL, PG_BIN=${PG_BIN}"
fi

# ====================== 2. 初始化 Control Plane PostgreSQL ======================
log "初始化 Control Plane PostgreSQL 实例 (port=${CP_PORT})…"
mkdir -p "${CP_DATA_DIR}" "${LOG_DIR}"
chown -R postgres:postgres "${CP_DATA_DIR}" 2>/dev/null || true

if [ ! -f "${CP_DATA_DIR}/PG_VERSION" ]; then
  sudo -u postgres "${PG_BIN}/initdb" -D "${CP_DATA_DIR}" -U "${CP_USER}" --auth=trust >/dev/null
fi
grep -q "^port = ${CP_PORT}" "${CP_DATA_DIR}/postgresql.conf" 2>/dev/null \
  || echo "port = ${CP_PORT}" >> "${CP_DATA_DIR}/postgresql.conf"
grep -q "^listen_addresses" "${CP_DATA_DIR}/postgresql.conf" 2>/dev/null \
  || echo "listen_addresses = 'localhost'" >> "${CP_DATA_DIR}/postgresql.conf"

# 启动 Control Plane PG
if sudo -u postgres "${PG_BIN}/pg_ctl" -D "${CP_DATA_DIR}" status >/dev/null 2>&1; then
  log "Control Plane PG 已在运行"
else
  if [ "${HAS_SYSTEMD}" -eq 1 ]; then
    # 用临时 systemd unit 启动 (持久化)
    cat > /etc/systemd/system/cloudpg-cp.service <<EOF
[Unit]
Description=CloudPG Control Plane PostgreSQL
After=network.target
[Service]
Type=forking
User=postgres
Group=postgres
Environment=PGDATA=${CP_DATA_DIR}
ExecStart=${PG_BIN}/pg_ctl -D ${CP_DATA_DIR} -l ${CP_DATA_DIR}/logfile -w start
ExecStop=${PG_BIN}/pg_ctl -D ${CP_DATA_DIR} -m fast -w stop
TimeoutSec=60
[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload
    systemctl enable --now cloudpg-cp.service
  else
    sudo -u postgres "${PG_BIN}/pg_ctl" -D "${CP_DATA_DIR}" -l "${CP_DATA_DIR}/logfile" start
  fi
  sleep 2
fi
# 建库
sudo -u postgres "${PG_BIN}/psql" -p "${CP_PORT}" -U "${CP_USER}" -tc "SELECT 1 FROM pg_database WHERE datname='cloudpg_cp'" | grep -q 1 \
  || sudo -u postgres "${PG_BIN}/psql" -p "${CP_PORT}" -U "${CP_USER}" -c "CREATE DATABASE cloudpg_cp;" >/dev/null
log "Control Plane PG 就绪"

# ====================== 3. 写入 .env ======================
log "写入 .env"
JWT_SECRET="$(openssl rand -hex 32)"
API_KEY_SECRET="$(openssl rand -hex 32)"
cat > "${PROJECT_DIR}/.env" <<EOF
# CloudPG Control Plane 配置 (由 install.sh 生成)
CLOUDPG_CONTROL_PLANE_DSN=postgresql://${CP_USER}:${CP_PASSWORD}@localhost:${CP_PORT}/cloudpg_cp
CLOUDPG_CP_PORT=${CP_PORT}
CLOUDPG_CP_USER=${CP_USER}
CLOUDPG_PG_BIN=${PG_BIN}
CLOUDPG_PG_VERSION=${PG_VERSION}
CLOUDPG_DATA_ROOT=/var/lib/cloudpg/instances
CLOUDPG_BASE_PORT=5432
CLOUDPG_PUBLIC_HOST=${PUBLIC_IP}
JWT_SECRET=${JWT_SECRET}
JWT_ALGORITHM=HS256
API_KEY_SECRET=${API_KEY_SECRET}
EOF

# ====================== 4. Python 后端 ======================
log "创建 Python 虚拟环境并安装依赖…"
if [ ! -x "${VENV_DIR}/bin/python" ]; then
  python3 -m venv "${VENV_DIR}"
fi
"${VENV_DIR}/bin/pip" install -q --upgrade pip
"${VENV_DIR}/bin/pip" install -q -r requirements.txt
# 安装项目内 SDK/CLI (若有)
[ -d packages/sdk-python ] && "${VENV_DIR}/bin/pip" install -q -e packages/sdk-python 2>/dev/null || true

log "初始化 Control Plane 数据表…"
"${VENV_DIR}/bin/python" -m db.init_db

log "创建管理员 / 组织 / Agent Key…"
"${VENV_DIR}/bin/python" -m db.seed_admin \
  --email "${ADMIN_EMAIL}" --password "${ADMIN_PASSWORD}" \
  --org "${SEED_ORG}" --org-name "${SEED_ORG_NAME}" || true

# ====================== 5. 前端构建 ======================
log "安装前端依赖并构建…"
cd "${PROJECT_DIR}/apps/web"
npm install -q
npm run build -q

# ====================== 6. systemd / 启动后端 ======================
log "启动后端 (uvicorn :${API_PORT})…"
if [ "${HAS_SYSTEMD}" -eq 1 ]; then
  cat > "${SYSTEMD_API}" <<EOF
[Unit]
Description=CloudPG Control Plane API
After=network.target cloudpg-cp.service
[Service]
Type=simple
User=${APP_USER}
WorkingDirectory=${PROJECT_DIR}
Environment=PATH=${VENV_DIR}/bin:/usr/bin:/bin
ExecStart=${VENV_DIR}/bin/uvicorn apps.api.main:app --host 127.0.0.1 --port ${API_PORT}
Restart=on-failure
RestartSec=5
[Install]
WantedBy=multi-user.target
EOF
  systemctl daemon-reload
  systemctl enable --now cloudpg-api.service
else
  nohup "${VENV_DIR}/bin/uvicorn" apps.api.main:app --host 127.0.0.1 --port ${API_PORT} \
    > "${LOG_DIR}/api.log" 2>&1 &
fi
sleep 3

# 启动前端 (next start)
log "启动前端 (next :${WEB_PORT})…"
if [ "${HAS_SYSTEMD}" -eq 1 ]; then
  cat > /etc/systemd/system/cloudpg-web.service <<EOF
[Unit]
Description=CloudPG Web Console
After=network.target
[Service]
Type=simple
User=${APP_USER}
WorkingDirectory=${PROJECT_DIR}/apps/web
ExecStart=/usr/bin/npx next start -p ${WEB_PORT}
Restart=on-failure
RestartSec=5
[Install]
WantedBy=multi-user.target
EOF
  systemctl daemon-reload
  systemctl enable --now cloudpg-web.service
else
  nohup /usr/bin/npx next start -p ${WEB_PORT} > "${LOG_DIR}/web.log" 2>&1 &
fi
sleep 3

# ====================== 7. Nginx 反代 ======================
log "配置 Nginx 反代…"
cat > "${NGINX_CONF}" <<EOF
server {
    listen 80;
    server_name _;

    # 前端
    location / {
        proxy_pass http://127.0.0.1:${WEB_PORT};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # 后端 API
    location /api/ {
        proxy_pass http://127.0.0.1:${API_PORT};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300s;
    }
}
EOF
if [ "${HAS_SYSTEMD}" -eq 1 ]; then
  systemctl enable --now nginx
else
  nginx -t && (nginx -s reload 2>/dev/null || nginx)
fi
nginx -t

# ====================== 8. 健康检查 ======================
log "健康检查…"
for i in $(seq 1 10); do
  if curl -fsS -o /dev/null "http://127.0.0.1:${API_PORT}/health"; then
    break
  fi
  sleep 2
done
curl -fsS -o /dev/null "http://127.0.0.1:${API_PORT}/health" \
  && log "后端 health OK" || warn "后端 health 未通过，请查看日志 ${LOG_DIR}/api.log"

echo
log "============ 部署完成 ============"
log "Web 控制台 : http://${PUBLIC_IP}/"
log "API 基地址 : http://${PUBLIC_IP}/api/v1"
log "管理员邮箱 : ${ADMIN_EMAIL}"
log "组织 slug  : ${SEED_ORG}"
log ""
log "Agent API Key 见上方 seed_admin 输出 (X-API-Key: org_...)。"
log "如配置域名，请将 Nginx server_name 改为你的域名，并补 TLS。"
log "=================================="

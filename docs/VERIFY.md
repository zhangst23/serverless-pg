# CloudPG 验证运行手册 (Phase 0 + Phase 1)

本手册说明如何在获得授权的环境（本地裸 VPS）中完成端到端验证。
代码已通过冒烟测试（应用加载、路由注册、纯逻辑），本手册补上"真实 PG 进程级"验证。

## 0. 准备

```bash
cd /root/serverless-pg
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt httpx pytest
```

## 1. 初始化底座 (Control Plane PG)

```bash
bash deploy/scripts/setup_base.sh        # initdb + 启动 control-plane PG(5433)
python -m db.init_db                       # 建 Control Plane 表
```

或手动等价操作（postgres 用户可写路径，如 /tmp/cloudpg）：

```bash
export PGBIN=/usr/pgsql/bin
sudo -u postgres $PGBIN/initdb -D /tmp/cloudpg/control-plane -U cloudpg --auth=trust
echo "port = 5433" >> /tmp/cloudpg/control-plane/postgresql.conf
sudo -u postgres $PGBIN/pg_ctl -D /tmp/cloudpg/control-plane -o "-p 5433" -l /tmp/cloudpg/control-plane/log -w start
python -m db.init_db
```

## 2. 启动 Control Plane

```bash
uvicorn apps.api.main:app --port 8000
```

## 3. 生成 API Key 并验证 6 大能力

```bash
export CLOUDPG_API=http://localhost:8000
export CLOUDPG_API_KEY=org_demo__proj_demo__demo123

# ① Database Lifecycle: 创建 (自动分配 Compute + Endpoint)
curl -X POST $CLOUDPG_API/api/v1/databases -H "X-API-Key: $CLOUDPG_API_KEY" \
  -d '{"name":"shop","cpu":1}' -H 'Content-Type: application/json'

# 查询数据库列表
curl $CLOUDPG_API/api/v1/databases -H "X-API-Key: $CLOUDPG_API_KEY"

# 执行 SQL (若挂起会自动 Resume)
DB_ID=$(curl $CLOUDPG_API/api/v1/databases -H "X-API-Key: $CLOUDPG_API_KEY" | python -c "import sys,json;print(json.load(sys.stdin)[0]['id'])")
curl -X POST $CLOUDPG_API/api/v1/databases/$DB_ID/query -H "X-API-Key: $CLOUDPG_API_KEY" \
  -d '{"sql":"CREATE TABLE t(id int); INSERT INTO t VALUES(1),(2); SELECT count(*) FROM t;"}' -H 'Content-Type: application/json'

# ② Serverless Compute 启停/挂起/恢复/调规格
curl -X POST $CLOUDPG_API/api/v1/computes/$COMP_ID/suspend -H "X-API-Key: $CLOUDPG_API_KEY"
curl -X POST $CLOUDPG_API/api/v1/computes/$COMP_ID/resume  -H "X-API-Key: $CLOUDPG_API_KEY"
curl -X PATCH $CLOUDPG_API/api/v1/computes/$COMP_ID -H "X-API-Key: $CLOUDPG_API_KEY" -d '{"cpu":2}' -H 'Content-Type: application/json'

# ④ Connection: 连接串
curl $CLOUDPG_API/api/v1/projects/demo/connection-string -H "X-API-Key: $CLOUDPG_API_KEY"

# ⑤ Backup: 手动备份
curl -X POST $CLOUDPG_API/api/v1/backups -H "X-API-Key: $CLOUDPG_API_KEY" -d "{\"database_id\":\"$DB_ID\"}" -H 'Content-Type: application/json'

# ⑥ Monitoring: 8 项指标
curl $CLOUDPG_API/api/v1/metrics/databases/$DB_ID -H "X-API-Key: $CLOUDPG_API_KEY"

# 删除 (释放资源)
curl -X DELETE $CLOUDPG_API/api/v1/databases/$DB_ID -H "X-API-Key: $CLOUDPG_API_KEY"
```

## 4. CLI 验证

```bash
python apps/cli/cloudpg.py projects
python apps/cli/cloudpg.py db create shop --cpu 1
python apps/cli/cloudpg.py db list
python apps/cli/cloudpg.py sql <DB_ID> "SELECT 1;"
python apps/cli/cloudpg.py warm <DB_ID>
```

## 5. 单元测试（无需 PG 进程）

```bash
python -m apps.api.test_smoke
```

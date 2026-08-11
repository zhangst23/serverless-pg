"use client";

import { useEffect, useState, Suspense } from "react";
import AppShell from "@/components/AppShell";
import { Card, Button, Badge, Spinner, ErrorBox, Empty, ConfirmDeleteModal } from "@/components/ui";
import { projects, parseToken, getToken } from "@/lib/api";
import { databases } from "@/lib/api";
import { useSearchParams } from "next/navigation";

export default function DatabasesPage() {
  return (
    <Suspense fallback={<Spinner label="加载中…" />}>
      <DatabasesInner />
    </Suspense>
  );
}

function DatabasesInner() {
  const [list, setList] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newCpu, setNewCpu] = useState(1);
  const [newStorage, setNewStorage] = useState(10);
  const [creating, setCreating] = useState(false);

  const [selected, setSelected] = useState<string | null>(null);
  const params = useSearchParams();

  const [deleteTarget, setDeleteTarget] = useState<{ id: string; name: string } | null>(null);
  const [deleting, setDeleting] = useState(false);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const d = await databases.list();
      setList(d);
      const preset = params.get("db");
      if (preset) setSelected(preset);
      else if (d.length && !selected) setSelected(d[0].id);
    } catch (e: any) {
      setError(e?.message || "加载失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function create() {
    if (!newName.trim()) return;
    setCreating(true);
    setError(null);
    try {
      await databases.create(newName.trim(), newCpu, newStorage);
      setNewName("");
      setShowCreate(false);
      await load();
    } catch (e: any) {
      setError(e?.message || "创建失败");
    } finally {
      setCreating(false);
    }
  }

  async function confirmRemove() {
    if (!deleteTarget) return;
    const id = deleteTarget.id;
    setDeleting(true);
    setError(null);
    try {
      await databases.remove(id);
      setDeleteTarget(null);
      if (selected === id) setSelected(null);
      await load();
    } catch (e: any) {
      setError(e?.message || "删除失败");
    } finally {
      setDeleting(false);
    }
  }

  async function downloadEnv(db: any) {
    try {
      const pid = parseToken(getToken())?.projectId || "";
      const cs = await projects.connectionString(pid);
      const uri: string = cs?.connection_string || "";
      // 将连接串中的库名替换为当前数据库名
      const env = [
        `# CloudPG database: ${db.name}`,
        `DATABASE_URL=${uri.replace(/\/[^/?]+(\?.*)?$/, `/${db.name}$1`)}`,
        `PGDATABASE=${db.name}`,
      ].join("\n");
      const blob = new Blob([env], { type: "text/plain" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${db.name}.env`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e: any) {
      setError(e?.message || "导出失败");
    }
  }

  return (
    <AppShell
      title="数据库"
      subtitle="Database Lifecycle · Serverless PostgreSQL 实例"
      actions={
        <Button onClick={() => setShowCreate((v) => !v)}>
          {showCreate ? "取消" : "+ 新建数据库"}
        </Button>
      }
    >
      {loading && <Spinner label="加载中…" />}
      <ErrorBox error={error} />

      {showCreate && (
        <Card className="mb-6" title="新建数据库">
          <div className="flex flex-wrap items-end gap-4">
            <Field label="名称">
              <input
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="shop"
                className="w-48 rounded-lg border border-[var(--border)] bg-[var(--panel-2)] px-3 py-2 text-sm outline-none focus:border-[var(--brand)]"
              />
            </Field>
            <Field label="CPU (0.25 - 4)">
              <input
                type="number"
                step="0.25"
                min="0.25"
                max="4"
                value={newCpu}
                onChange={(e) => setNewCpu(Number(e.target.value))}
                className="w-32 rounded-lg border border-[var(--border)] bg-[var(--panel-2)] px-3 py-2 text-sm outline-none focus:border-[var(--brand)]"
              />
            </Field>
            <Field label="存储 (10GB - 1TB)">
              <select
                value={newStorage}
                onChange={(e) => setNewStorage(Number(e.target.value))}
                className="w-32 rounded-lg border border-[var(--border)] bg-[var(--panel-2)] px-3 py-2 text-sm outline-none focus:border-[var(--brand)]"
              >
                {[10, 50, 100, 500, 1024].map((g) => (
                  <option key={g} value={g}>
                    {g >= 1024 ? "1 TB" : `${g} GB`}
                  </option>
                ))}
              </select>
            </Field>
            <Button onClick={create} disabled={creating}>
              {creating ? "创建中…" : "创建"}
            </Button>
          </div>
        </Card>
      )}

      {!loading && list.length === 0 && !showCreate && (
        <Empty>暂无数据库，点击右上角「新建数据库」开始。</Empty>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {list.map((db) => (
          <Card
            key={db.id}
            title={db.name}
            actions={
              <div className="flex items-center gap-2">
                <Badge tone={db.status === "active" ? "ok" : "warn"}>
                  {db.status}
                </Badge>
                <Button
                  variant="ghost"
                  onClick={() => setSelected(db.id)}
                  className="px-2 py-1 text-xs"
                >
                  查询
                </Button>
                <Button
                  variant="ghost"
                  onClick={() => downloadEnv(db)}
                  className="px-2 py-1 text-xs"
                >
                  .env
                </Button>
                <Button
                  variant="danger"
                  onClick={() => setDeleteTarget({ id: db.id, name: db.name })}
                  className="px-2 py-1 text-xs"
                >
                  删除
                </Button>
              </div>
            }
          >
            <div className="text-xs text-[var(--muted)]">
              ID: <span className="font-mono">{db.id}</span>
            </div>
          </Card>
        ))}
      </div>

      {selected && (
        <SqlConsole
          databaseId={selected}
          databaseName={list.find((d) => d.id === selected)?.name || selected}
          reload={load}
        />
      )}

      {deleteTarget && (
        <ConfirmDeleteModal
          resourceName={deleteTarget.name}
          busy={deleting}
          onCancel={() => !deleting && setDeleteTarget(null)}
          onConfirm={confirmRemove}
        />
      )}
    </AppShell>
  );
}

function SqlConsole({
  databaseId,
  databaseName,
  reload,
}: {
  databaseId: string;
  databaseName: string;
  reload: () => void;
}) {
  const [sql, setSql] = useState("SELECT 1;");
  const [rows, setRows] = useState<any[] | null>(null);
  const [running, setRunning] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const suggestedSql: { label: string; sql: string }[] = [
    { label: "查看所有表", sql: "SELECT schemaname, tablename\nFROM pg_tables\nWHERE schemaname NOT IN ('pg_catalog', 'information_schema')\nORDER BY schemaname, tablename;" },
    { label: "查看表结构", sql: "SELECT column_name, data_type, is_nullable, column_default\nFROM information_schema.columns\nWHERE table_name = '<表名>'\nORDER BY ordinal_position;" },
    { label: "查看索引", sql: "SELECT indexname, indexdef\nFROM pg_indexes\nWHERE tablename = '<表名>';" },
    { label: "查看数据库大小", sql: "SELECT pg_size_pretty(pg_database_size(current_database())) AS db_size;" },
    { label: "查看活跃连接", sql: "SELECT pid, usename, application_name, state, query\nFROM pg_stat_activity\nWHERE pid <> pg_backend_pid()\nORDER BY pid;" },
    { label: "查看表行数估计", sql: "SELECT relname AS table_name, n_live_tup AS estimated_rows\nFROM pg_stat_user_tables\nORDER BY n_live_tup DESC;" },
    { label: "创建表", sql: "CREATE TABLE <表名> (\n  id BIGSERIAL PRIMARY KEY,\n  created_at TIMESTAMPTZ NOT NULL DEFAULT now()\n);" },
    { label: "查看版本", sql: "SELECT version();" },
  ];

  async function run() {
    setRunning(true);
    setErr(null);
    setRows(null);
    try {
      const res = await databases.query(databaseId, sql);
      setRows(res.rows);
    } catch (e: any) {
      setErr(e?.message || "执行失败");
    } finally {
      setRunning(false);
      reload();
    }
  }

  return (
    <Card className="mt-6" title="SQL 控制台" subtitle={`数据库 ${databaseName}`}>
      <div className="mb-3 flex flex-wrap gap-2">
        <span className="text-xs text-[var(--muted)]">常用 SQL：</span>
        {suggestedSql.map((s) => (
          <Button
            key={s.label}
            variant="ghost"
            className="px-2 py-1 text-xs"
            onClick={() => setSql(s.sql)}
          >
            {s.label}
          </Button>
        ))}
      </div>
      <textarea
        value={sql}
        onChange={(e) => setSql(e.target.value)}
        rows={4}
        className="w-full rounded-lg border border-[var(--border)] bg-[var(--panel-2)] p-3 font-mono text-sm outline-none focus:border-[var(--brand)]"
      />
      <div className="mt-3 flex items-center gap-3">
        <Button onClick={run} disabled={running}>
          {running ? "执行中…" : "运行 ▶"}
        </Button>
        <ErrorBox error={err} />
      </div>

      {rows !== null && (
        <div className="mt-4 overflow-x-auto rounded-lg border border-[var(--border)]">
          <table className="w-full text-left text-sm">
            <tbody>
              {rows.map((row, i) => (
                <tr key={i} className="border-b border-[var(--border)]">
                  <td className="px-3 py-2 font-mono text-[var(--muted)]">
                    {JSON.stringify(row)}
                  </td>
                </tr>
              ))}
              {rows.length === 0 && (
                <tr>
                  <td className="px-3 py-3 text-[var(--muted)]">空结果集</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs text-[var(--muted)]">{label}</span>
      {children}
    </label>
  );
}

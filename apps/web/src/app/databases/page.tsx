"use client";

import { useEffect, useState, Suspense } from "react";
import AppShell from "@/components/AppShell";
import { Card, Button, Badge, Spinner, ErrorBox, Empty } from "@/components/ui";
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
  const [creating, setCreating] = useState(false);

  const [selected, setSelected] = useState<string | null>(null);
  const params = useSearchParams();

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
      await databases.create(newName.trim(), newCpu);
      setNewName("");
      setShowCreate(false);
      await load();
    } catch (e: any) {
      setError(e?.message || "创建失败");
    } finally {
      setCreating(false);
    }
  }

  async function remove(id: string) {
    if (!confirm("确认删除该数据库？此操作不可恢复。")) return;
    setError(null);
    try {
      await databases.remove(id);
      if (selected === id) setSelected(null);
      await load();
    } catch (e: any) {
      setError(e?.message || "删除失败");
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
                  variant="danger"
                  onClick={() => remove(db.id)}
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

      {selected && <SqlConsole databaseId={selected} reload={load} />}
    </AppShell>
  );
}

function SqlConsole({
  databaseId,
  reload,
}: {
  databaseId: string;
  reload: () => void;
}) {
  const [sql, setSql] = useState("SELECT 1;");
  const [rows, setRows] = useState<any[] | null>(null);
  const [running, setRunning] = useState(false);
  const [err, setErr] = useState<string | null>(null);

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
    <Card className="mt-6" title="SQL 控制台" subtitle={`数据库 ${databaseId}`}>
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

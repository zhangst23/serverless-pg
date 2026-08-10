"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { Card, Button, Spinner, ErrorBox, Empty } from "@/components/ui";
import { databases } from "@/lib/api";

export default function TablesPage() {
  const [dbs, setDbs] = useState<any[]>([]);
  const [dbId, setDbId] = useState<string>("");
  const [tables, setTables] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadDbs() {
    setError(null);
    try {
      const list = await databases.list();
      setDbs(list);
      if (list.length && !dbId) setDbId(list[0].id);
    } catch (e: any) {
      setError(e?.message || "加载失败");
    }
  }

  useEffect(() => {
    loadDbs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function loadTables() {
    if (!dbId) return;
    setLoading(true);
    setError(null);
    try {
      const t = await databases.tables(dbId);
      setTables(t);
    } catch (e: any) {
      setError(e?.message || "加载失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (dbId) loadTables();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dbId]);

  return (
    <AppShell
      title="表浏览"
      subtitle="Tables · 查看数据库中的用户表"
      actions={
        <select
          value={dbId}
          onChange={(e) => setDbId(e.target.value)}
          className="rounded-lg border border-[var(--border)] bg-[var(--panel-2)] px-3 py-2 text-sm outline-none focus:border-[var(--brand)]"
        >
          {dbs.map((d) => (
            <option key={d.id} value={d.id}>
              {d.name}
            </option>
          ))}
        </select>
      }
    >
      <ErrorBox error={error} />
      {loading && <Spinner label="加载中…" />}

      {!loading && tables.length === 0 && (
        <Empty>该数据库暂无用户表，或实例处于挂起态（已自动唤醒，请重试）。</Empty>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {tables.map((t) => (
          <Card key={t.name} title={t.name}>
            <div className="text-xs text-[var(--muted)]">
              表 <span className="font-mono text-[var(--foreground)]">{t.name}</span>
            </div>
          </Card>
        ))}
      </div>
    </AppShell>
  );
}

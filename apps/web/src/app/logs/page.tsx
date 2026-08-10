"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { Card, Button, Spinner, ErrorBox, Empty } from "@/components/ui";
import { databases } from "@/lib/api";

export default function LogsPage() {
  const [dbs, setDbs] = useState<any[]>([]);
  const [dbId, setDbId] = useState<string>("");
  const [log, setLog] = useState<string>("");
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

  async function loadLogs() {
    if (!dbId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await databases.logs(dbId, 300);
      setLog(res.log || "");
    } catch (e: any) {
      setError(e?.message || "加载失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (dbId) loadLogs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dbId]);

  return (
    <AppShell
      title="日志"
      subtitle="Logs · PostgreSQL 实例运行日志"
      actions={
        <div className="flex items-center gap-3">
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
          <Button onClick={loadLogs} disabled={loading || !dbId}>
            {loading ? "刷新中…" : "刷新"}
          </Button>
        </div>
      }
    >
      <ErrorBox error={error} />
      {loading && <Spinner label="加载中…" />}

      {!loading && !log && <Empty>暂无日志（实例可能未启动）。</Empty>}

      {log && (
        <Card title="PG 日志 (logfile)" subtitle="最近 300 行">
          <pre className="max-h-[70vh] overflow-auto rounded-lg bg-black/40 p-4 font-mono text-xs leading-relaxed text-[var(--muted)] whitespace-pre-wrap">
            {log}
          </pre>
        </Card>
      )}
    </AppShell>
  );
}

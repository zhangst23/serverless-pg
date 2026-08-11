"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { Card, Button, Badge, Spinner, ErrorBox, Empty } from "@/components/ui";
import { backups, databases } from "@/lib/api";

export default function BackupsPage() {
  const [list, setList] = useState<any[]>([]);
  const [dbList, setDbList] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [target, setTarget] = useState("");

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [b, d] = await Promise.all([backups.list(), databases.list()]);
      setList(b);
      setDbList(d);
      if (d.length && !target) setTarget(d[0].id);
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
    if (!target) return;
    setBusy(true);
    setError(null);
    try {
      await backups.create(target);
      await load();
    } catch (e: any) {
      setError(e?.message || "备份失败");
    } finally {
      setBusy(false);
    }
  }

  async function restore(id: string) {
    if (!confirm("确认从该备份恢复？将覆盖当前数据库数据。")) return;
    setError(null);
    try {
      await backups.restore(id);
      await load();
    } catch (e: any) {
      setError(e?.message || "恢复失败");
    }
  }

  async function download(id: string) {
    setError(null);
    try {
      await backups.download(id);
    } catch (e: any) {
      setError(e?.message || "下载失败");
    }
  }

  async function remove(id: string) {
    if (!confirm("确认删除该备份？此操作不可撤销。")) return;
    setError(null);
    try {
      await backups.remove(id);
      await load();
    } catch (e: any) {
      setError(e?.message || "删除失败");
    }
  }

  return (
    <AppShell
      title="备份"
      subtitle="Backup · 手动备份 / 恢复"
      actions={
        <div className="flex items-center gap-2">
          <select
            value={target}
            onChange={(e) => setTarget(e.target.value)}
            className="rounded-lg border border-[var(--border)] bg-[var(--panel-2)] px-3 py-2 text-sm outline-none"
          >
            {dbList.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
          <Button onClick={create} disabled={busy || !dbList.length}>
            {busy ? "备份中…" : "手动备份"}
          </Button>
        </div>
      }
    >
      {loading && <Spinner label="加载中…" />}
      <ErrorBox error={error} />

      {!loading && list.length === 0 && (
        <Empty>暂无备份记录。选择一个数据库并点击「手动备份」。</Empty>
      )}

      <div className="space-y-3">
        {list.map((b) => (
          <Card key={b.id}>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium">
                  {b.name || b.database_name}
                </div>
                <div className="mt-0.5 text-xs text-[var(--muted)]">
                  {b.database_name}
                  {b.created_at
                    ? ` · ${new Date(b.created_at).toLocaleString("zh-CN", { hour12: false })}`
                    : ""}
                </div>
                <div className="mt-1 flex items-center gap-2">
                  <Badge tone={b.kind === "manual" ? "brand" : "neutral"}>
                    {b.kind}
                  </Badge>
                  <Badge tone={b.status === "completed" ? "ok" : "warn"}>
                    {b.status}
                  </Badge>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="soft"
                  onClick={() => restore(b.id)}
                  disabled={b.status !== "completed"}
                >
                  恢复
                </Button>
                <Button
                  variant="ghost"
                  onClick={() => download(b.id)}
                  disabled={b.status !== "completed"}
                >
                  下载
                </Button>
                <Button
                  variant="ghost"
                  onClick={() => remove(b.id)}
                >
                  删除
                </Button>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </AppShell>
  );
}

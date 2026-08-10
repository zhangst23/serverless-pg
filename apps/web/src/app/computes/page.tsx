"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { Card, Button, Badge, Spinner, ErrorBox, Empty } from "@/components/ui";
import { databases, computes, metrics } from "@/lib/api";

export default function ComputesPage() {
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const dbs = await databases.list();
      const enriched = await Promise.all(
        dbs
          .filter((d) => d.compute_id)
          .map(async (d) => {
            let cpu = "—";
            try {
              const m = await metrics.forDatabase(d.id);
              cpu = m.cpu ?? "—";
            } catch {
              /* ignore */
            }
            return { ...d, cpu };
          })
      );
      setItems(enriched);
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

  async function act(computeId: string, fn: () => Promise<any>, label: string) {
    setBusy(computeId + label);
    setError(null);
    try {
      await fn();
      await load();
    } catch (e: any) {
      setError(e?.message || "操作失败");
    } finally {
      setBusy(null);
    }
  }

  return (
    <AppShell
      title="计算实例"
      subtitle="Serverless Compute · 启停 / 挂起 / 恢复 / 调规格"
      actions={<Button onClick={load}>刷新</Button>}
    >
      {loading && <Spinner label="加载中…" />}
      <ErrorBox error={error} />

      {!loading && items.length === 0 && (
        <Empty>暂无关联计算实例。创建数据库会自动分配一个 Serverless Compute。</Empty>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {items.map((it) => (
          <Card key={it.compute_id} title={it.name}>
            <div className="mb-4 flex flex-wrap items-center gap-2">
              <Badge tone={it.status === "active" ? "ok" : "warn"}>
                {it.status}
              </Badge>
              <span className="text-xs text-[var(--muted)]">
                CPU 分配：{it.cpu}
              </span>
              <span className="text-xs text-[var(--muted)]">
                实例：{it.compute_id}
              </span>
            </div>

            <div className="flex flex-wrap gap-2">
              <Button
                variant="soft"
                disabled={busy !== null}
                onClick={() =>
                  act(it.compute_id, () => computes.resume(it.compute_id), "resume")
                }
              >
                ▶ 恢复
              </Button>
              <Button
                variant="soft"
                disabled={busy !== null}
                onClick={() =>
                  act(it.compute_id, () => computes.suspend(it.compute_id), "suspend")
                }
              >
                ⏸ 挂起
              </Button>
              <Button
                variant="soft"
                disabled={busy !== null}
                onClick={() =>
                  act(it.compute_id, () => computes.restart(it.compute_id), "restart")
                }
              >
                ↻ 重启
              </Button>
            </div>

            <div className="mt-4 border-t border-[var(--border)] pt-4">
              <div className="mb-2 text-xs text-[var(--muted)]">调整规格</div>
              <div className="flex items-center gap-2">
                {[0.5, 1, 2, 4].map((c) => (
                  <Button
                    key={c}
                    variant="ghost"
                    className="px-3 py-1 text-xs"
                    disabled={busy !== null}
                    onClick={() =>
                      act(
                        it.compute_id,
                        () => computes.resize(it.compute_id, c),
                        "resize" + c
                      )
                    }
                  >
                    {c} CPU
                  </Button>
                ))}
              </div>
            </div>
            {busy === it.compute_id + "resize" + 4 && (
              <p className="mt-2 text-xs text-amber-300">调规格会重启实例…</p>
            )}
          </Card>
        ))}
      </div>
    </AppShell>
  );
}

"use client";

import { useEffect, useState, useRef } from "react";
import AppShell from "@/components/AppShell";
import { Card, Button, Badge, Spinner, ErrorBox, Empty } from "@/components/ui";
import { databases, metrics } from "@/lib/api";

type Metric = {
  label: string;
  key: string;
  unit?: string;
  format?: (v: any) => string;
  tone?: (v: number) => "ok" | "warn" | "err" | "neutral";
};

const METRICS: Metric[] = [
  { label: "CPU 使用率", key: "cpu", unit: "vCPU", format: (v) => Number(v).toFixed(2) },
  { label: "活跃连接数", key: "connections", unit: "", format: (v) => String(v) },
  { label: "存储用量", key: "storage_used_gb", unit: "GB", format: (v) => Number(v).toFixed(2) },
  { label: "存储上限", key: "storage_limit_gb", unit: "GB", format: (v) => Number(v).toFixed(0) },
  { label: "读 IOPS", key: "iops_read", unit: "", format: (v) => String(v) },
  { label: "写 IOPS", key: "iops_write", unit: "", format: (v) => String(v) },
  { label: "每秒查询", key: "queries_per_sec", unit: "qps", format: (v) => String(v) },
  {
    label: "缓存命中率",
    key: "cache_hit_ratio",
    unit: "%",
    format: (v) => Number(v).toFixed(1),
  },
];

export default function MonitoringPage() {
  const [dbList, setDbList] = useState<any[]>([]);
  const [dbId, setDbId] = useState("");
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [auto, setAuto] = useState(false);
  const timer = useRef<any>(null);

  async function loadDbs() {
    const d = await databases.list();
    setDbList(d);
    if (d.length) setDbId(d[0].id);
  }

  async function loadMetrics(id: string) {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      setData(await metrics.forDatabase(id));
    } catch (e: any) {
      setError(e?.message || "加载失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDbs().then(() => {
      if (dbList.length) loadMetrics(dbList[0].id);
    });
    return () => timer.current && clearInterval(timer.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (auto && dbId) {
      timer.current = setInterval(() => loadMetrics(dbId), 5000);
      return () => clearInterval(timer.current);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [auto, dbId]);

  const storagePct =
    data && data.storage_limit_gb
      ? (data.storage_used_gb / data.storage_limit_gb) * 100
      : 0;

  return (
    <AppShell
      title="监控"
      subtitle="Monitoring · 8 项核心指标"
      actions={
        <div className="flex items-center gap-3">
          <select
            value={dbId}
            onChange={(e) => setDbId(e.target.value)}
            className="rounded-lg border border-[var(--border)] bg-[var(--panel-2)] px-3 py-2 text-sm outline-none"
          >
            {dbList.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
          <Button
            variant={auto ? "primary" : "ghost"}
            onClick={() => setAuto((v) => !v)}
          >
            {auto ? "自动刷新中" : "自动刷新"}
          </Button>
          <Button onClick={() => loadMetrics(dbId)}>刷新</Button>
        </div>
      }
    >
      {loading && <Spinner label="加载中…" />}
      <ErrorBox error={error} />

      {!loading && !data && (
        <Empty>暂无监控数据。请先创建数据库。</Empty>
      )}

      {data && (
        <>
          <div className="mb-4">
            <div className="mb-1 flex items-center justify-between text-xs text-[var(--muted)]">
              <span>存储用量</span>
              <span>
                {Number(data.storage_used_gb).toFixed(2)} /{" "}
                {Number(data.storage_limit_gb).toFixed(0)} GB (
                {storagePct.toFixed(1)}%)
              </span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-[var(--panel-2)]">
              <div
                className="h-full rounded-full bg-[var(--brand)]"
                style={{ width: `${Math.min(storagePct, 100)}%` }}
              />
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {METRICS.map((m) => {
              const raw = data[m.key];
              const val = raw === undefined || raw === null ? "—" : m.format!(raw);
              return (
                <div
                  key={m.key}
                  className="rounded-xl border border-[var(--border)] bg-[var(--panel)] p-4"
                >
                  <div className="text-xs text-[var(--muted)]">{m.label}</div>
                  <div className="mt-2 flex items-baseline gap-1">
                    <span className="text-2xl font-semibold">{val}</span>
                    {m.unit && (
                      <span className="text-xs text-[var(--muted)]">
                        {m.unit}
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}
    </AppShell>
  );
}

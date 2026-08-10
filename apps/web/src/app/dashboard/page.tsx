"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import AppShell from "@/components/AppShell";
import { Card, Spinner, ErrorBox, Button, Badge } from "@/components/ui";
import { projects, databases, backups, computes } from "@/lib/api";

export default function DashboardPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState({
    projects: 0,
    databases: 0,
    backups: 0,
    dbList: [] as any[],
  });

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [p, d, b] = await Promise.all([
        projects.list(),
        databases.list(),
        backups.list(),
      ]);
      setStats({ projects: p.length, databases: d.length, backups: b.length, dbList: d });
    } catch (e: any) {
      setError(e?.message || "加载失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <AppShell
      title="概览"
      subtitle="CloudPG Serverless PostgreSQL 平台总览"
      actions={<Button onClick={load}>刷新</Button>}
    >
      {loading && <Spinner label="加载中…" />}
      <ErrorBox error={error} />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard label="项目" value={stats.projects} href="/dashboard" />
        <StatCard label="数据库" value={stats.databases} href="/databases" />
        <StatCard label="备份" value={stats.backups} href="/backups" />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2" title="最近数据库">
          {stats.dbList.length === 0 ? (
            <p className="text-sm text-[var(--muted)]">
              还没有数据库。前往
              <Link href="/databases" className="text-[var(--brand)]">
                {" "}
                数据库页{" "}
              </Link>
              创建你的第一个 Serverless PostgreSQL。
            </p>
          ) : (
            <div className="space-y-2">
              {stats.dbList.slice(0, 5).map((db) => (
                <Link
                  key={db.id}
                  href={`/databases?db=${db.id}`}
                  className="flex items-center justify-between rounded-lg border border-[var(--border)] bg-[var(--panel-2)] px-4 py-3 hover:bg-white/5"
                >
                  <div>
                    <div className="text-sm font-medium">{db.name}</div>
                    <div className="text-xs text-[var(--muted)]">{db.id}</div>
                  </div>
                  <Badge tone={db.status === "active" ? "ok" : "warn"}>
                    {db.status}
                  </Badge>
                </Link>
              ))}
            </div>
          )}
        </Card>

        <Card title="快捷操作">
          <div className="space-y-2">
            <Link href="/databases">
              <Button className="w-full">+ 新建数据库</Button>
            </Link>
            <Link href="/backups">
              <Button variant="soft" className="w-full">
                管理备份
              </Button>
            </Link>
            <Link href="/monitoring">
              <Button variant="soft" className="w-full">
                查看监控
              </Button>
            </Link>
          </div>
        </Card>
      </div>
    </AppShell>
  );
}

function StatCard({
  label,
  value,
  href,
}: {
  label: string;
  value: number;
  href: string;
}) {
  return (
    <Link href={href}>
      <div className="rounded-xl border border-[var(--border)] bg-[var(--panel)] p-5 hover:bg-white/5">
        <div className="text-sm text-[var(--muted)]">{label}</div>
        <div className="mt-2 text-3xl font-semibold">{value}</div>
      </div>
    </Link>
  );
}

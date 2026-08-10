"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { Card, Button, Spinner, ErrorBox } from "@/components/ui";
import { getApiKey, parseApiKey, projects } from "@/lib/api";

export default function SettingsPage() {
  const [neverSuspend, setNeverSuspend] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);

  const parsed = parseApiKey(getApiKey());
  const projectId = parsed?.projectId || "";

  async function load() {
    if (!projectId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const info = await projects.get(projectId);
      if (info && !info.error) setNeverSuspend(!!info.never_suspend);
    } catch (e: any) {
      setError(e?.message || "加载失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  async function toggle(value: boolean) {
    if (!projectId) return;
    setSaving(true);
    setError(null);
    setOk(null);
    try {
      await projects.neverSuspend(projectId, value);
      setNeverSuspend(value);
      setOk(value ? "已设为「永不自动暂停」" : "已恢复为允许自动暂停");
    } catch (e: any) {
      setError(e?.message || "保存失败");
    } finally {
      setSaving(false);
    }
  }

  return (
    <AppShell title="设置" subtitle="Settings · 项目级配置">
      <ErrorBox error={error} />
      {ok && (
        <div className="mb-4 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-4 py-2 text-sm text-emerald-300">
          {ok}
        </div>
      )}
      {loading && <Spinner label="加载中…" />}

      <Card title="自动暂停策略" subtitle="Serverless 计算实例在空闲后会自动挂起以释放资源">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">永不自动暂停</div>
            <div className="mt-1 text-xs text-[var(--muted)]">
              开启后，该项目的计算实例将保持运行，不会因空闲而挂起（适用于需极低延迟的生产库）。
            </div>
          </div>
          <label className="relative inline-flex cursor-pointer items-center">
            <input
              type="checkbox"
              className="peer sr-only"
              checked={neverSuspend}
              disabled={saving || loading}
              onChange={(e) => toggle(e.target.checked)}
            />
            <div className="h-6 w-11 rounded-full bg-[var(--border)] peer-checked:bg-[var(--brand)] peer-disabled:opacity-50" />
            <div className="absolute left-0.5 top-0.5 h-5 w-5 rounded-full bg-white transition peer-checked:translate-x-5" />
          </label>
        </div>
      </Card>

      <Card title="项目信息" className="mt-6">
        <div className="space-y-2 text-sm">
          <div>
            <span className="text-[var(--muted)]">Project ID: </span>
            <span className="font-mono">{projectId || "—"}</span>
          </div>
          <div>
            <span className="text-[var(--muted)]">Organization ID: </span>
            <span className="font-mono">{parsed?.organizationId || "—"}</span>
          </div>
        </div>
      </Card>
    </AppShell>
  );
}

"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { Card, Button, Spinner, ErrorBox, Empty, Badge, Modal } from "@/components/ui";
import { databases, performance } from "@/lib/api";

type Tab = "extensions" | "settings";

export default function PerformancePage() {
  const [dbs, setDbs] = useState<any[]>([]);
  const [dbId, setDbId] = useState<string>("");
  const [tab, setTab] = useState<Tab>("extensions");
  const [error, setError] = useState<string | null>(null);

  const [busy, setBusy] = useState(false);

  useEffect(() => {
    loadDbs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function loadDbs() {
    try {
      const list = await databases.list();
      setDbs(list);
      if (list.length && !dbId) setDbId(list[0].id);
    } catch (e: any) {
      setError(e?.message || "加载数据库失败");
    }
  }

  return (
    <AppShell
      title="PG性能"
      subtitle="管理提升 PostgreSQL 性能的扩展(插件)与运行参数"
      actions={
        <select
          value={dbId}
          onChange={(e) => setDbId(e.target.value)}
          className="rounded-lg border border-[var(--border)] bg-[var(--panel-2)] px-3 py-2 text-sm outline-none focus:border-[var(--brand)]"
        >
          {dbs.length === 0 && <option value="">无数据库</option>}
          {dbs.map((d) => (
            <option key={d.id} value={d.id}>
              {d.name}
            </option>
          ))}
        </select>
      }
    >
      <ErrorBox error={error} />

      {!dbId ? (
        <Empty>请先创建一个数据库，再管理其 PG 性能</Empty>
      ) : (
        <>
          <div className="mb-5 flex gap-2">
            <TabButton active={tab === "extensions"} onClick={() => { setTab("extensions"); setError(null); }}>
              扩展 / 插件
            </TabButton>
            <TabButton active={tab === "settings"} onClick={() => { setTab("settings"); setError(null); }}>
              性能参数
            </TabButton>
          </div>

          {tab === "extensions" && (
            <ExtensionsPanel
              dbId={dbId}
              busy={busy}
              setBusy={setBusy}
              onError={setError}
            />
          )}
          {tab === "settings" && (
            <SettingsPanel
              dbId={dbId}
              busy={busy}
              setBusy={setBusy}
              onError={setError}
            />
          )}
        </>
      )}
    </AppShell>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`rounded-lg px-4 py-2 text-sm font-medium transition ${
        active
          ? "bg-[var(--brand)]/10 text-[var(--brand)]"
          : "text-[var(--muted)] hover:bg-white/5"
      }`}
    >
      {children}
    </button>
  );
}

/* ---------------- 扩展 / 插件 ---------------- */
function ExtensionsPanel({
  dbId,
  busy,
  setBusy,
  onError,
}: {
  dbId: string;
  busy: boolean;
  setBusy: (b: boolean) => void;
  onError: (e: string | null) => void;
}) {
  const [installed, setInstalled] = useState<any[]>([]);
  const [available, setAvailable] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [showInstall, setShowInstall] = useState(false);
  const [installName, setInstallName] = useState("");

  async function load() {
    setLoading(true);
    onError(null);
    try {
      const data = await performance.listExtensions(dbId);
      setInstalled(data.installed || []);
      setAvailable(data.available || []);
    } catch (e: any) {
      onError(e?.message || "加载扩展失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (dbId) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dbId]);

  async function doInstall() {
    if (!installName.trim()) return;
    setBusy(true);
    onError(null);
    try {
      await performance.installExtension(installName.trim(), dbId);
      setShowInstall(false);
      setInstallName("");
      await load();
    } catch (e: any) {
      onError(e?.message || "安装扩展失败");
    } finally {
      setBusy(false);
    }
  }

  async function doDrop(name: string) {
    if (!confirm(`确认卸载扩展 "${name}"？依赖此扩展的对象可能失效。`)) return;
    setBusy(true);
    onError(null);
    try {
      await performance.dropExtension(name, dbId);
      await load();
    } catch (e: any) {
      onError(e?.message || "卸载扩展失败");
    } finally {
      setBusy(false);
    }
  }

  const notInstalled = available.filter((a) => !a.installed);

  return (
    <div className="space-y-4">
      <Card
        title="已安装扩展"
        subtitle="当前数据库已启用的扩展，可在此卸载"
        actions={
          <Button onClick={() => setShowInstall(true)} disabled={busy || loading}>
            + 安装扩展
          </Button>
        }
      >
        {loading && <Spinner label="加载中…" />}
        {!loading && installed.length === 0 && (
          <Empty>尚未安装任何扩展</Empty>
        )}
        {!loading && installed.length > 0 && (
          <div className="overflow-x-auto rounded-lg border border-[var(--border)]">
            <table className="w-full text-left text-sm">
              <thead className="bg-[var(--panel-2)]">
                <tr>
                  <th className="px-3 py-2 font-medium text-[var(--muted)]">名称</th>
                  <th className="px-3 py-2 font-medium text-[var(--muted)]">Schema</th>
                  <th className="px-3 py-2 font-medium text-[var(--muted)]">版本</th>
                  <th className="px-3 py-2 font-medium text-[var(--muted)]">操作</th>
                </tr>
              </thead>
              <tbody>
                {installed.map((r) => (
                  <tr key={r.name} className="border-t border-[var(--border)]">
                    <td className="px-3 py-2 font-mono text-[var(--brand)]">{r.name}</td>
                    <td className="px-3 py-2 font-mono text-xs">{r.schema}</td>
                    <td className="px-3 py-2 font-mono text-xs">{r.version}</td>
                    <td className="px-3 py-2">
                      <Button variant="danger" onClick={() => doDrop(r.name)} disabled={busy}>
                        卸载
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card title="可用扩展" subtitle="实例支持但尚未安装的扩展，点击安装以提升性能或能力">
        {loading && <Spinner label="加载中…" />}
        {!loading && notInstalled.length === 0 && (
          <Empty>已安装全部可用扩展</Empty>
        )}
        {!loading && notInstalled.length > 0 && (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
            {notInstalled.map((a) => (
              <div
                key={a.name}
                className="flex flex-col rounded-lg border border-[var(--border)] p-4"
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-sm font-semibold text-[var(--foreground)]">
                    {a.name}
                  </span>
                  <Badge tone="neutral">v{a.version}</Badge>
                </div>
                <p className="mt-2 flex-1 text-xs text-[var(--muted)] leading-relaxed">
                  {a.comment || "提升 PostgreSQL 能力的扩展"}
                </p>
                <Button
                  className="mt-3"
                  onClick={() => {
                    setInstallName(a.name);
                    setShowInstall(true);
                  }}
                  disabled={busy}
                >
                  安装
                </Button>
              </div>
            ))}
          </div>
        )}
      </Card>

      {showInstall && (
        <Modal title="安装扩展" onClose={() => setShowInstall(false)}>
          <label className="text-xs text-[var(--muted)]">扩展名称</label>
          <input
            autoFocus
            value={installName}
            onChange={(e) => setInstallName(e.target.value)}
            placeholder="例如 pg_stat_statements"
            className="mt-1 w-full rounded-lg border border-[var(--border)] bg-[var(--panel-2)] px-3 py-2 text-sm outline-none focus:border-[var(--brand)]"
          />
          <p className="mt-2 text-xs text-[var(--muted)]">
            将从 pg_available_extensions 中安装该扩展到当前数据库。扩展名需存在于实例中。
          </p>
          <div className="mt-4 flex justify-end gap-3">
            <Button variant="ghost" onClick={() => setShowInstall(false)} disabled={busy}>
              取消
            </Button>
            <Button onClick={doInstall} disabled={busy || !installName.trim()}>
              {busy ? "安装中…" : "安装"}
            </Button>
          </div>
        </Modal>
      )}
    </div>
  );
}

/* ---------------- 性能参数 ---------------- */
function SettingsPanel({
  dbId,
  busy,
  setBusy,
  onError,
}: {
  dbId: string;
  busy: boolean;
  setBusy: (b: boolean) => void;
  onError: (e: string | null) => void;
}) {
  const [rows, setRows] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [editing, setEditing] = useState<any | null>(null);
  const [newValue, setNewValue] = useState("");
  const [scope, setScope] = useState<"database" | "system">("database");

  async function load() {
    setLoading(true);
    onError(null);
    try {
      const data = await performance.listSettings(dbId);
      setRows(data.settings || []);
    } catch (e: any) {
      onError(e?.message || "加载参数失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (dbId) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dbId]);

  function openEdit(r: any) {
    setEditing(r);
    setNewValue(r.current_value);
    setScope("database");
  }

  async function doSave() {
    if (!editing) return;
    setBusy(true);
    onError(null);
    try {
      await performance.setSetting(editing.name, newValue.trim(), dbId, scope);
      setEditing(null);
      await load();
    } catch (e: any) {
      onError(e?.message || "设置参数失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card title="性能参数" subtitle="调整常用的 PostgreSQL 运行参数 (仅暴露对性能影响明显且安全的项)">
      {loading && <Spinner label="加载中…" />}
      {!loading && rows.length === 0 && <Empty>无可调整参数</Empty>}
      {!loading && rows.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-[var(--border)]">
          <table className="w-full text-left text-sm">
            <thead className="bg-[var(--panel-2)]">
              <tr>
                <th className="px-3 py-2 font-medium text-[var(--muted)]">参数</th>
                <th className="px-3 py-2 font-medium text-[var(--muted)]">当前值</th>
                <th className="px-3 py-2 font-medium text-[var(--muted)]">类型</th>
                <th className="px-3 py-2 font-medium text-[var(--muted)]">说明</th>
                <th className="px-3 py-2 font-medium text-[var(--muted)]">操作</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.name} className="border-t border-[var(--border)]">
                  <td className="px-3 py-2 font-mono text-xs text-[var(--brand)]">{r.name}</td>
                  <td className="px-3 py-2 font-mono text-xs">{r.display}</td>
                  <td className="px-3 py-2 text-xs text-[var(--muted)]">{r.vartype}</td>
                  <td className="px-3 py-2 text-xs text-[var(--muted)]">{r.description}</td>
                  <td className="px-3 py-2">
                    <Button variant="soft" onClick={() => openEdit(r)} disabled={busy}>
                      调整
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {editing && (
        <Modal title={`调整参数 · ${editing.name}`} onClose={() => setEditing(null)}>
          <p className="mb-2 text-xs text-[var(--muted)]">{editing.description}</p>
          <label className="text-xs text-[var(--muted)]">新值</label>
          <input
            autoFocus
            value={newValue}
            onChange={(e) => setNewValue(e.target.value)}
            className="mt-1 w-full rounded-lg border border-[var(--border)] bg-[var(--panel-2)] px-3 py-2 text-sm outline-none focus:border-[var(--brand)]"
          />
          <label className="mt-3 block text-xs text-[var(--muted)]">应用范围</label>
          <select
            value={scope}
            onChange={(e) => setScope(e.target.value as "database" | "system")}
            className="mt-1 w-full rounded-lg border border-[var(--border)] bg-[var(--panel-2)] px-3 py-2 text-sm outline-none focus:border-[var(--brand)]"
          >
            <option value="database">数据库级 (ALTER DATABASE，仅当前库)</option>
            <option value="system">实例级 (ALTER SYSTEM，需 reload 生效)</option>
          </select>
          <div className="mt-4 flex justify-end gap-3">
            <Button variant="ghost" onClick={() => setEditing(null)} disabled={busy}>
              取消
            </Button>
            <Button onClick={doSave} disabled={busy || !newValue.trim()}>
              {busy ? "保存中…" : "保存"}
            </Button>
          </div>
        </Modal>
      )}
    </Card>
  );
}

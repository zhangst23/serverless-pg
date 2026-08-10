"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { Card, Button, Badge, Spinner, ErrorBox, Empty } from "@/components/ui";
import { projects } from "@/lib/api";

const SNIPPET_LABELS: Record<string, string> = {
  connection_string: "连接串",
  env: "环境变量",
  node: "Node.js",
  python: "Python",
  go: "Go",
  rust: "Rust",
};

export default function ConnectionsPage() {
  const [projectList, setProjectList] = useState<any[]>([]);
  const [projectId, setProjectId] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [conn, setConn] = useState<any>(null);
  const [roles, setRoles] = useState<any[]>([]);
  const [roleName, setRoleName] = useState("");
  const [rolePriv, setRolePriv] = useState("readwrite");
  const [busy, setBusy] = useState(false);
  const [newRole, setNewRole] = useState<any>(null);

  async function loadProjects() {
    setLoading(true);
    setError(null);
    try {
      const p = await projects.list();
      setProjectList(p);
      if (p.length) {
        const id = p[0].id;
        setProjectId(id);
        await loadConn(id);
        await loadRoles(id);
      }
    } catch (e: any) {
      setError(e?.message || "加载失败");
    } finally {
      setLoading(false);
    }
  }

  async function loadConn(id: string) {
    try {
      setConn(await projects.connectionString(id));
    } catch (e: any) {
      setError(e?.message || "获取连接串失败");
    }
  }
  async function loadRoles(id: string) {
    try {
      setRoles(await projects.roles(id));
    } catch {
      setRoles([]);
    }
  }

  useEffect(() => {
    loadProjects();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function switchProject(id: string) {
    setProjectId(id);
    await Promise.all([loadConn(id), loadRoles(id)]);
  }

  async function createRole() {
    if (!roleName.trim() || !projectId) return;
    setBusy(true);
    setError(null);
    try {
      const r = await projects.createRole(projectId, roleName.trim(), rolePriv);
      setNewRole(r);
      setRoleName("");
      await loadRoles(projectId);
    } catch (e: any) {
      setError(e?.message || "创建角色失败");
    } finally {
      setBusy(false);
    }
  }

  async function resetRole(roleId: string) {
    if (!projectId) return;
    setError(null);
    try {
      const r = await projects.resetRole(projectId, roleId);
      setNewRole(r);
      await loadRoles(projectId);
    } catch (e: any) {
      setError(e?.message || "重置失败");
    }
  }

  async function delRole(roleId: string) {
    if (!projectId) return;
    setError(null);
    try {
      await projects.deleteRole(projectId, roleId);
      await loadRoles(projectId);
    } catch (e: any) {
      setError(e?.message || "删除失败");
    }
  }

  return (
    <AppShell
      title="连接 & 角色"
      subtitle="Connection String · 多语言连接片段 · 数据库角色"
      actions={
        projectList.length > 0 && (
          <select
            value={projectId}
            onChange={(e) => switchProject(e.target.value)}
            className="rounded-lg border border-[var(--border)] bg-[var(--panel-2)] px-3 py-2 text-sm outline-none"
          >
            {projectList.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} ({p.id})
              </option>
            ))}
          </select>
        )
      }
    >
      {loading && <Spinner label="加载中…" />}
      <ErrorBox error={error} />

      {!loading && projectList.length === 0 && (
        <Empty>暂无项目。请先在「概览」或后端创建项目。</Empty>
      )}

      {conn && (
        <Card className="mb-6" title="连接串 (Connection String)">
          <Copyable value={conn.connection_string} />
          <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
            {Object.entries(SNIPPET_LABELS).map(([k, label]) =>
              conn.snippets?.[k] ? (
                <div
                  key={k}
                  className="rounded-lg border border-[var(--border)] bg-[var(--panel-2)] p-3"
                >
                  <div className="mb-1 text-xs font-medium text-[var(--muted)]">
                    {label}
                  </div>
                  <pre className="overflow-x-auto whitespace-pre-wrap break-all font-mono text-xs">
                    {conn.snippets[k]}
                  </pre>
                </div>
              ) : null
            )}
          </div>
        </Card>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card title="创建角色" subtitle="为应用分配独立数据库账号">
          <div className="flex flex-wrap items-end gap-3">
            <label className="block">
              <span className="mb-1 block text-xs text-[var(--muted)]">
                角色名
              </span>
              <input
                value={roleName}
                onChange={(e) => setRoleName(e.target.value)}
                placeholder="app_role"
                className="w-44 rounded-lg border border-[var(--border)] bg-[var(--panel-2)] px-3 py-2 text-sm outline-none focus:border-[var(--brand)]"
              />
            </label>
            <label className="block">
              <span className="mb-1 block text-xs text-[var(--muted)]">
                权限
              </span>
              <select
                value={rolePriv}
                onChange={(e) => setRolePriv(e.target.value)}
                className="rounded-lg border border-[var(--border)] bg-[var(--panel-2)] px-3 py-2 text-sm outline-none"
              >
                <option value="readwrite">读写</option>
                <option value="readonly">只读</option>
              </select>
            </label>
            <Button onClick={createRole} disabled={busy}>
              {busy ? "创建中…" : "创建"}
            </Button>
          </div>
          {newRole && (
            <div className="mt-4 rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3">
              <div className="mb-1 text-xs font-medium text-emerald-300">
                已创建角色：{newRole.name}
              </div>
              <Copyable value={newRole.snippets.connection_string} />
            </div>
          )}
        </Card>

        <Card title="角色列表">
          {roles.length === 0 ? (
            <p className="text-sm text-[var(--muted)]">暂无角色。</p>
          ) : (
            <div className="space-y-2">
              {roles.map((r) => (
                <div
                  key={r.id}
                  className="flex items-center justify-between rounded-lg border border-[var(--border)] bg-[var(--panel-2)] px-4 py-3"
                >
                  <div>
                    <div className="text-sm font-medium">{r.name}</div>
                    <Badge tone={r.privilege === "readonly" ? "warn" : "brand"}>
                      {r.privilege}
                    </Badge>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="ghost"
                      className="px-2 py-1 text-xs"
                      onClick={() => resetRole(r.id)}
                    >
                      重置密码
                    </Button>
                    <Button
                      variant="danger"
                      className="px-2 py-1 text-xs"
                      onClick={() => delRole(r.id)}
                    >
                      删除
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </AppShell>
  );
}

function Copyable({ value }: { value: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <div className="flex items-center gap-2">
      <code className="flex-1 break-all rounded-lg border border-[var(--border)] bg-[var(--panel-2)] px-3 py-2 font-mono text-xs">
        {value}
      </code>
      <Button
        variant="ghost"
        className="px-2 py-1 text-xs"
        onClick={() => {
          navigator.clipboard?.writeText(value);
          setCopied(true);
          setTimeout(() => setCopied(false), 1200);
        }}
      >
        {copied ? "已复制" : "复制"}
      </Button>
    </div>
  );
}

"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { setApiKey, getApiKey, API_BASE, projects } from "@/lib/api";
import { Button, ErrorBox } from "@/components/ui";

export default function LoginPage() {
  const router = useRouter();
  const [key, setKey] = useState(getApiKey());
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!key.trim()) {
      setError("请输入 API Key");
      return;
    }
    setLoading(true);
    try {
      setApiKey(key.trim());
      // 验证 Key 可访问项目列表
      await projects.list();
      router.push("/dashboard");
    } catch (err: any) {
      setError(err?.message || "登录失败");
      setLoading(false);
    }
  };

  return (
    <div className="grid min-h-screen place-items-center bg-[var(--background)] px-4">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 grid h-14 w-14 place-items-center rounded-2xl bg-[var(--brand)] text-2xl font-bold text-slate-900">
            P
          </div>
          <h1 className="text-xl font-semibold">CloudPG 控制台</h1>
          <p className="mt-1 text-sm text-[var(--muted)]">
            AI-Native Serverless PostgreSQL
          </p>
        </div>

        <form
          onSubmit={onSubmit}
          className="rounded-2xl border border-[var(--border)] bg-[var(--panel)] p-6"
        >
          <label className="mb-2 block text-sm font-medium">API Key</label>
          <input
            value={key}
            onChange={(e) => setKey(e.target.value)}
            placeholder="org_xxx__proj_xxx__abc123"
            className="w-full rounded-lg border border-[var(--border)] bg-[var(--panel-2)] px-3 py-2.5 text-sm outline-none focus:border-[var(--brand)]"
          />
          <p className="mt-2 text-xs text-[var(--muted)]">
            格式：<code>org_&lt;组织&gt;__proj_&lt;项目&gt;__&lt;随机&gt;</code>
            <br />
            后端地址：{API_BASE}
          </p>

          <ErrorBox error={error} />
          <Button
            onClick={onSubmit as any}
            disabled={loading}
            className="mt-4 w-full"
          >
            {loading ? "验证中…" : "进入控制台"}
          </Button>
        </form>
      </div>
    </div>
  );
}

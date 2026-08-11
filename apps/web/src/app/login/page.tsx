"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { setToken, getToken, API_BASE } from "@/lib/api";
import { Button, ErrorBox } from "@/components/ui";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!email.trim() || !password) {
      setError("请输入邮箱与密码");
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim(), password }),
        cache: "no-store",
      });
      if (!res.ok) {
        let detail = "登录失败";
        try {
          detail = (await res.json()).detail || detail;
        } catch {
          /* ignore */
        }
        throw new Error(detail);
      }
      const data = await res.json();
      setToken(data.access_token);
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
          <label className="mb-2 block text-sm font-medium">邮箱</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@org.com"
            className="w-full rounded-lg border border-[var(--border)] bg-[var(--panel-2)] px-3 py-2.5 text-sm outline-none focus:border-[var(--brand)]"
          />

          <label className="mb-2 mt-4 block text-sm font-medium">密码</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            className="w-full rounded-lg border border-[var(--border)] bg-[var(--panel-2)] px-3 py-2.5 text-sm outline-none focus:border-[var(--brand)]"
          />

          <p className="mt-3 text-xs text-[var(--muted)]">
            用户通道（账密）· 后端地址：{API_BASE}
            <br />
            CLI / SDK 仍使用 X-API-Key（Agent 通道）。
          </p>

          <ErrorBox error={error} />
          <Button disabled={loading} className="mt-4 w-full">
            {loading ? "登录中…" : "进入控制台"}
          </Button>
        </form>
      </div>
    </div>
  );
}

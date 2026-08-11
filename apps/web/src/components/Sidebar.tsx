"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { clearToken } from "@/lib/api";

const NAV = [
  { href: "/dashboard", label: "概览", icon: "📊" },
  { href: "/databases", label: "数据库", icon: "🗄️" },
  { href: "/tables", label: "数据表", icon: "📋" },
  { href: "/performance", label: "PG性能", icon: "🚀" },
  { href: "/computes", label: "计算实例", icon: "⚡" },
  { href: "/connections", label: "连接 & 角色", icon: "🔌" },
  { href: "/backups", label: "备份", icon: "💾" },
  { href: "/monitoring", label: "监控", icon: "📈" },
  { href: "/logs", label: "日志", icon: "📜" },
  { href: "/settings", label: "设置", icon: "⚙️" },
];

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();

  const logout = () => {
    clearToken();
    router.push("/login");
  };

  return (
    <aside className="flex h-screen w-60 flex-col border-r border-[var(--border)] bg-[var(--panel-2)]">
      <div className="flex items-center gap-2 px-5 py-5">
        <div className="grid h-9 w-9 place-items-center rounded-lg bg-[var(--brand)] text-slate-900 font-bold">
          P
        </div>
        <div>
          <div className="text-sm font-semibold leading-none">CloudPG</div>
          <div className="text-[10px] text-[var(--muted)] mt-1">
            Serverless Postgres
          </div>
        </div>
      </div>

      <nav className="flex-1 space-y-1 px-3">
        {NAV.map((item) => {
          const active =
            pathname === item.href || pathname.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition ${
                active
                  ? "bg-[var(--brand)]/10 text-[var(--brand)]"
                  : "text-[var(--muted)] hover:bg-white/5 hover:text-[var(--foreground)]"
              }`}
            >
              <span className="text-base">{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-[var(--border)] p-3">
        <button
          onClick={logout}
          className="w-full rounded-lg border border-[var(--border)] px-3 py-2 text-sm text-[var(--muted)] hover:bg-white/5 hover:text-[var(--foreground)]"
        >
          退出登录
        </button>
      </div>
    </aside>
  );
}

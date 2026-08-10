"use client";

import { ReactNode } from "react";
import Sidebar from "@/components/Sidebar";
import AuthGuard from "@/components/AuthGuard";

export default function AppShell({
  children,
  title,
  subtitle,
  actions,
}: {
  children: ReactNode;
  title?: string;
  subtitle?: string;
  actions?: ReactNode;
}) {
  return (
    <AuthGuard>
      <div className="flex h-screen overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-y-auto">
          {(title || actions) && (
            <header className="sticky top-0 z-10 flex items-center justify-between border-b border-[var(--border)] bg-[var(--background)]/80 px-8 py-5 backdrop-blur">
              <div>
                {title && (
                  <h1 className="text-lg font-semibold">{title}</h1>
                )}
                {subtitle && (
                  <p className="text-xs text-[var(--muted)] mt-0.5">
                    {subtitle}
                  </p>
                )}
              </div>
              {actions}
            </header>
          )}
          <div className="p-8">{children}</div>
        </main>
      </div>
    </AuthGuard>
  );
}

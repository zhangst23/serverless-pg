"use client";

import { ReactNode, useState } from "react";

export function Card({
  children,
  className = "",
  title,
  subtitle,
  actions,
}: {
  children: ReactNode;
  className?: string;
  title?: string;
  subtitle?: string;
  actions?: ReactNode;
}) {
  return (
    <div
      className={`rounded-xl border border-[var(--border)] bg-[var(--panel)] p-5 ${className}`}
    >
      {(title || actions) && (
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            {title && (
              <h3 className="text-sm font-semibold text-[var(--foreground)]">
                {title}
              </h3>
            )}
            {subtitle && (
              <p className="text-xs text-[var(--muted)] mt-0.5">{subtitle}</p>
            )}
          </div>
          {actions}
        </div>
      )}
      {children}
    </div>
  );
}

export function Button({
  children,
  onClick,
  variant = "primary",
  disabled,
  className = "",
  title,
}: {
  children: ReactNode;
  onClick?: () => void;
  variant?: "primary" | "ghost" | "danger" | "soft";
  disabled?: boolean;
  className?: string;
  title?: string;
}) {
  const base =
    "inline-flex items-center justify-center gap-1.5 rounded-lg px-3.5 py-2 text-sm font-medium transition disabled:opacity-50 disabled:cursor-not-allowed";
  const variants: Record<string, string> = {
    primary:
      "bg-[var(--brand)] text-slate-900 hover:bg-[var(--brand-2)] shadow-sm shadow-sky-500/20",
    ghost:
      "border border-[var(--border)] text-[var(--foreground)] hover:bg-white/5",
    danger:
      "bg-rose-500/10 text-rose-300 border border-rose-500/30 hover:bg-rose-500/20",
    soft: "bg-white/5 text-[var(--foreground)] hover:bg-white/10",
  };
  return (
    <button
      title={title}
      disabled={disabled}
      onClick={onClick}
      className={`${base} ${variants[variant]} ${className}`}
    >
      {children}
    </button>
  );
}

export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "ok" | "warn" | "err" | "brand";
}) {
  const tones: Record<string, string> = {
    neutral: "bg-white/5 text-[var(--muted)] border-[var(--border)]",
    ok: "bg-emerald-500/10 text-emerald-300 border-emerald-500/30",
    warn: "bg-amber-500/10 text-amber-300 border-amber-500/30",
    err: "bg-rose-500/10 text-rose-300 border-rose-500/30",
    brand: "bg-sky-500/10 text-sky-300 border-sky-500/30",
  };
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${tones[tone]}`}
    >
      {children}
    </span>
  );
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 text-sm text-[var(--muted)]">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-[var(--border)] border-t-[var(--brand)]" />
      {label}
    </div>
  );
}

export function ErrorBox({ error }: { error: string | null }) {
  if (!error) return null;
  return (
    <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-300">
      {error}
    </div>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-lg border border-dashed border-[var(--border)] px-4 py-10 text-center text-sm text-[var(--muted)]">
      {children}
    </div>
  );
}

export function Modal({
  title,
  children,
  onClose,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md rounded-xl border border-[var(--border)] bg-[var(--panel)] p-5 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="mb-4 text-sm font-semibold text-[var(--foreground)]">
          {title}
        </h3>
        {children}
      </div>
    </div>
  );
}

export function ConfirmDeleteModal({
  resourceName,
  onCancel,
  onConfirm,
  busy,
}: {
  resourceName: string;
  onCancel: () => void;
  onConfirm: () => void;
  busy?: boolean;
}) {
  const [text, setText] = useState("");
  const matched = text.trim() === "删除";
  return (
    <Modal title="删除确认" onClose={onCancel}>
      <p className="text-sm text-[var(--muted)]">
        此操作不可恢复。请输入{" "}
        <span className="font-mono font-semibold text-rose-300">删除</span>{" "}
        以确认删除 <span className="font-mono text-[var(--foreground)]">{resourceName}</span>。
      </p>
      <input
        autoFocus
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="删除"
        className="mt-3 w-full rounded-lg border border-[var(--border)] bg-[var(--panel-2)] px-3 py-2 text-sm outline-none focus:border-rose-500/50"
      />
      <div className="mt-4 flex justify-end gap-3">
        <Button variant="ghost" onClick={onCancel} disabled={busy}>
          取消
        </Button>
        <Button variant="danger" onClick={onConfirm} disabled={!matched || busy}>
          {busy ? "删除中…" : "确认删除"}
        </Button>
      </div>
    </Modal>
  );
}

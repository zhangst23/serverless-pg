"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { Card, Button, Spinner, ErrorBox, Empty } from "@/components/ui";
import { databases } from "@/lib/api";

function splitName(raw: string): { schema: string; table: string } {
  // 表名可能是 "public.test2" 或 "test2"
  const idx = raw.indexOf(".");
  if (idx > 0) {
    return { schema: raw.slice(0, idx), table: raw.slice(idx + 1) };
  }
  return { schema: "public", table: raw };
}

function quoteIdent(name: string): string {
  return '"' + name.replace(/"/g, '""') + '"';
}

export default function TablesPage() {
  const [dbs, setDbs] = useState<any[]>([]);
  // 展开状态: 哪些库已展开(显示其表)
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  // 各库表缓存
  const [tablesByDb, setTablesByDb] = useState<Record<string, any[]>>({});
  const [loadingDb, setLoadingDb] = useState<string | null>(null);

  const [selectedDb, setSelectedDb] = useState<string>("");
  const [activeTable, setActiveTable] = useState<string>("");
  const [rows, setRows] = useState<any[]>([]);
  const [columns, setColumns] = useState<string[]>([]);
  const [loadingRows, setLoadingRows] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadDbs() {
    setError(null);
    try {
      const list = await databases.list();
      setDbs(list);
    } catch (e: any) {
      setError(e?.message || "加载失败");
    }
  }

  useEffect(() => {
    loadDbs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function toggleDb(dbId: string) {
    if (expanded[dbId]) {
      setExpanded((p) => ({ ...p, [dbId]: false }));
      return;
    }
    setExpanded((p) => ({ ...p, [dbId]: true }));
    if (tablesByDb[dbId]) return;
    setLoadingDb(dbId);
    setError(null);
    try {
      const t = await databases.tables(dbId);
      setTablesByDb((p) => ({ ...p, [dbId]: t }));
    } catch (e: any) {
      setError(e?.message || "加载表失败");
    } finally {
      setLoadingDb(null);
    }
  }

  async function openTable(dbId: string, rawName: string) {
    setSelectedDb(dbId);
    setActiveTable(rawName);
    setLoadingRows(true);
    setError(null);
    setRows([]);
    setColumns([]);
    try {
      const { schema, table } = splitName(rawName);
      const sql = `SELECT * FROM ${quoteIdent(schema)}.${quoteIdent(table)} LIMIT 100`;
      const res = await databases.query(dbId, sql);
      const r = res.rows || [];
      setRows(r);
      setColumns(r.length ? Object.keys(r[0]) : []);
    } catch (e: any) {
      setError(e?.message || "查询失败");
    } finally {
      setLoadingRows(false);
    }
  }

  return (
    <AppShell title="表浏览" subtitle="Tables · 左侧选择数据表，右侧查看内容">
      <ErrorBox error={error} />

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-[300px_1fr]">
        {/* 左侧：数据库 + 表树 */}
        <Card className="self-start" title="数据库 / 数据表">
          <ul className="max-h-[72vh] space-y-1 overflow-y-auto pr-1">
            {dbs.map((d) => {
              const isOpen = !!expanded[d.id];
              const tables = tablesByDb[d.id] || [];
              return (
                <li key={d.id}>
                  <button
                    onClick={() => toggleDb(d.id)}
                    className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm font-medium transition hover:bg-[var(--panel-2)]"
                  >
                    <span className="text-[var(--muted)]">{isOpen ? "▾" : "▸"}</span>
                    <span className="truncate">{d.name}</span>
                    {loadingDb === d.id && (
                      <span className="ml-auto text-xs text-[var(--muted)]">…</span>
                    )}
                  </button>
                  {isOpen && (
                    <ul className="ml-5 border-l border-[var(--border)] pl-2">
                      {tables.length === 0 && loadingDb !== d.id && (
                        <li className="px-2 py-1 text-xs text-[var(--muted)]">
                          无表
                        </li>
                      )}
                      {tables.map((t) => {
                        const name: string = t.name;
                        const active = activeTable === name && selectedDb === d.id;
                        return (
                          <li key={name}>
                            <button
                              onClick={() => openTable(d.id, name)}
                              className={`flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm transition ${
                                active
                                  ? "bg-[var(--brand)]/15 text-[var(--brand)]"
                                  : "text-[var(--foreground)] hover:bg-[var(--panel-2)]"
                              }`}
                            >
                              <span className="text-[var(--muted)]">▦</span>
                              <span className="truncate font-mono">{name}</span>
                            </button>
                          </li>
                        );
                      })}
                    </ul>
                  )}
                </li>
              );
            })}
            {dbs.length === 0 && (
              <li className="px-2 py-2 text-xs text-[var(--muted)]">无数据库</li>
            )}
          </ul>
        </Card>

        {/* 右侧：表内容 */}
        <Card
          className="self-start"
          title={
            selectedDb && activeTable
              ? `${dbName(selectedDb, dbs)} · ${activeTable}`
              : "表内容"
          }
        >
          {!activeTable && <Empty>从左侧选择一个数据表查看其内容</Empty>}
          {activeTable && loadingRows && <Spinner label="查询中…" />}
          {activeTable && !loadingRows && columns.length > 0 && (
            <div className="overflow-x-auto rounded-lg border border-[var(--border)]">
              <table className="w-full text-left text-sm">
                <thead className="bg-[var(--panel-2)]">
                  <tr>
                    {columns.map((c) => (
                      <th
                        key={c}
                        className="whitespace-nowrap border-b border-[var(--border)] px-3 py-2 font-medium text-[var(--muted)]"
                      >
                        {c}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row, i) => (
                    <tr key={i} className="border-b border-[var(--border)]">
                      {columns.map((c) => (
                        <td
                          key={c}
                          className="whitespace-nowrap px-3 py-2 font-mono text-xs"
                        >
                          {formatCell(row[c])}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="px-3 py-2 text-xs text-[var(--muted)]">
                显示前 {rows.length} 行
              </div>
            </div>
          )}
          {activeTable && !loadingRows && columns.length === 0 && (
            <Empty>空表（无数据）</Empty>
          )}
        </Card>
      </div>
    </AppShell>
  );
}

function dbName(dbId: string, dbs: any[]): string {
  return dbs.find((d) => d.id === dbId)?.name || dbId;
}

function formatCell(v: any): string {
  if (v === null || v === undefined) return "NULL";
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}

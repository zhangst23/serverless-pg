"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { Card, Button, Spinner, ErrorBox, Empty } from "@/components/ui";
import { databases } from "@/lib/api";

export default function TablesPage() {
  const [dbs, setDbs] = useState<any[]>([]);
  const [dbId, setDbId] = useState<string>("");
  const [tables, setTables] = useState<any[]>([]);
  const [activeTable, setActiveTable] = useState<string>("");
  const [rows, setRows] = useState<any[]>([]);
  const [columns, setColumns] = useState<string[]>([]);
  const [loadingTables, setLoadingTables] = useState(false);
  const [loadingRows, setLoadingRows] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadDbs() {
    setError(null);
    try {
      const list = await databases.list();
      setDbs(list);
      if (list.length && !dbId) setDbId(list[0].id);
    } catch (e: any) {
      setError(e?.message || "加载失败");
    }
  }

  useEffect(() => {
    loadDbs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function loadTables() {
    if (!dbId) return;
    setLoadingTables(true);
    setError(null);
    setActiveTable("");
    setRows([]);
    setColumns([]);
    try {
      const t = await databases.tables(dbId);
      setTables(t);
    } catch (e: any) {
      setError(e?.message || "加载失败");
    } finally {
      setLoadingTables(false);
    }
  }

  useEffect(() => {
    if (dbId) loadTables();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dbId]);

  async function openTable(name: string) {
    if (!dbId) return;
    setActiveTable(name);
    setLoadingRows(true);
    setError(null);
    setRows([]);
    setColumns([]);
    try {
      const res = await databases.query(
        dbId,
        `SELECT * FROM "${name}" LIMIT 100`
      );
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
    <AppShell
      title="表浏览"
      subtitle="Tables · 左侧选择数据表，右侧查看内容"
      actions={
        <select
          value={dbId}
          onChange={(e) => setDbId(e.target.value)}
          className="rounded-lg border border-[var(--border)] bg-[var(--panel-2)] px-3 py-2 text-sm outline-none focus:border-[var(--brand)]"
        >
          {dbs.map((d) => (
            <option key={d.id} value={d.id}>
              {d.name}
            </option>
          ))}
        </select>
      }
    >
      <ErrorBox error={error} />

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-[280px_1fr]">
        {/* 左侧：表列表 */}
        <Card className="self-start" title="数据表">
          {loadingTables && <Spinner label="加载中…" />}
          {!loadingTables && tables.length === 0 && (
            <p className="text-xs text-[var(--muted)]">
              该数据库暂无用户表，或实例处于挂起态（已自动唤醒，请重试）。
            </p>
          )}
          <ul className="max-h-[70vh] space-y-1 overflow-y-auto pr-1">
            {tables.map((t) => (
              <li key={t.name}>
                <button
                  onClick={() => openTable(t.name)}
                  className={`flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm transition ${
                    activeTable === t.name
                      ? "bg-[var(--brand)]/15 text-[var(--brand)]"
                      : "text-[var(--foreground)] hover:bg-[var(--panel-2)]"
                  }`}
                >
                  <span className="text-[var(--muted)]">▦</span>
                  <span className="truncate font-mono">{t.name}</span>
                </button>
              </li>
            ))}
          </ul>
        </Card>

        {/* 右侧：表内容 */}
        <Card className="self-start" title={activeTable ? `表：${activeTable}` : "表内容"}>
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

function formatCell(v: any): string {
  if (v === null || v === undefined) return "NULL";
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}

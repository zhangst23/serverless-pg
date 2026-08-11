// CloudPG 前端 API 客户端
// 两类凭证:
//  - User 通道 (Web 控制台): 账密登录后拿 Session JWT，存 localStorage，
//    每次请求带 Authorization: Bearer <jwt>
//  - Agent 通道 (CLI/SDK 不在此前端): X-API-Key

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE || "";

export const TOKEN_STORAGE = "cloudpg_token";

export function getToken(): string {
  if (typeof window === "undefined") return "";
  return window.localStorage.getItem(TOKEN_STORAGE) || "";
}

export function setToken(token: string) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(TOKEN_STORAGE, token);
}

export function clearToken() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(TOKEN_STORAGE);
}

/** 解析 Session JWT payload (仅读 claims，信任来自登录时后端签发)。 */
export function parseToken(token: string): {
  organizationId: string;
  projectId: string | null;
  userId: string;
} | null {
  if (!token) return null;
  try {
    const part = token.split(".")[1];
    const json = atob(part.replace(/-/g, "+").replace(/_/g, "/"));
    const claims = JSON.parse(json);
    return {
      organizationId: claims.organization_id || "",
      projectId: claims.project_id || null,
      userId: claims.sub || "",
    };
  } catch {
    return null;
  }
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(
  path: string,
  opts: RequestInit = {}
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(opts.headers as Record<string, string>),
  };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 12000);
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...opts,
      headers,
      cache: "no-store",
      signal: controller.signal,
    });
  } catch (e: any) {
    clearTimeout(timeout);
    if (e?.name === "AbortError") {
      throw new ApiError("请求超时，无法连接后端 (检查 NEXT_PUBLIC_API_BASE 与后端是否运行)", 0);
    }
    throw new ApiError(e?.message || "网络错误，无法连接后端", 0);
  }
  clearTimeout(timeout);

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(detail, res.status);
  }

  if (res.status === 204) return undefined as T;
  const text = await res.text();
  return text ? (JSON.parse(text) as T) : (undefined as T);
}

/* ---------------- Projects ---------------- */
export const projects = {
  list: () => request<any[]>("/api/v1/projects", { method: "GET" }),
  get: (id: string) =>
    request<any>(`/api/v1/projects/${id}`, { method: "GET" }),
  create: (name: string, region = "local") =>
    request<any>("/api/v1/projects", {
      method: "POST",
      body: JSON.stringify({ name, region }),
    }),
  connectionString: (projectId: string) =>
    request<any>(`/api/v1/projects/${projectId}/connection-string`, {
      method: "GET",
    }),
  neverSuspend: (projectId: string, value: boolean) =>
    request<any>(`/api/v1/projects/${projectId}/never-suspend?value=${value}`, {
      method: "PATCH",
    }),
  roles: (projectId: string) =>
    request<any>(`/api/v1/projects/${projectId}/roles`, { method: "GET" }),
  createRole: (projectId: string, name: string, privilege = "readwrite") =>
    request<any>(`/api/v1/projects/${projectId}/roles`, {
      method: "POST",
      body: JSON.stringify({ name, privilege }),
    }),
  resetRole: (projectId: string, roleId: string) =>
    request<any>(
      `/api/v1/projects/${projectId}/roles/${roleId}/reset-password`,
      { method: "POST" }
    ),
  deleteRole: (projectId: string, roleId: string) =>
    request<any>(`/api/v1/projects/${projectId}/roles/${roleId}`, {
      method: "DELETE",
    }),
};

/* ---------------- Databases ---------------- */
export const databases = {
  list: () => request<any[]>("/api/v1/databases", { method: "GET" }),
  create: (name: string, cpu = 1, storageGb = 10) =>
    request<any>("/api/v1/databases", {
      method: "POST",
      body: JSON.stringify({ name, cpu, storage_gb: storageGb }),
    }),
  get: (id: string) =>
    request<any>(`/api/v1/databases/${id}`, { method: "GET" }),
  connectionString: (id: string, host?: string) =>
    request<any>(
      `/api/v1/databases/${id}/connection-string${
        host ? `?host=${encodeURIComponent(host)}` : ""
      }`,
      { method: "GET" }
    ),
  remove: (id: string) =>
    request<any>(`/api/v1/databases/${id}`, { method: "DELETE" }),
  query: (id: string, sql: string) =>
    request<{ rows: any[] }>(`/api/v1/databases/${id}/query`, {
      method: "POST",
      body: JSON.stringify({ sql }),
    }),
  tables: (id: string) =>
    request<any[]>(`/api/v1/databases/${id}/tables`, { method: "GET" }),
  logs: (id: string, tail = 200) =>
    request<{ log: string }>(`/api/v1/databases/${id}/logs?tail=${tail}`, {
      method: "GET",
    }),
};

/* ---------------- Computes ---------------- */
export const computes = {
  create: (name: string, cpu = 1) =>
    request<any>("/api/v1/computes", {
      method: "POST",
      body: JSON.stringify({ name, cpu }),
    }),
  start: (id: string) =>
    request<any>(`/api/v1/computes/${id}/start`, { method: "POST" }),
  stop: (id: string) =>
    request<any>(`/api/v1/computes/${id}/stop`, { method: "POST" }),
  suspend: (id: string) =>
    request<any>(`/api/v1/computes/${id}/suspend`, { method: "POST" }),
  resume: (id: string) =>
    request<any>(`/api/v1/computes/${id}/resume`, { method: "POST" }),
  restart: (id: string) =>
    request<any>(`/api/v1/computes/${id}/restart`, { method: "POST" }),
  resize: (id: string, cpu: number) =>
    request<any>(`/api/v1/computes/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ cpu }),
    }),
  autoSuspend: (id: string, autoSuspend: boolean) =>
    request<any>(`/api/v1/computes/${id}/auto-suspend`, {
      method: "PATCH",
      body: JSON.stringify({ auto_suspend: autoSuspend }),
    }),
};

/* ---------------- Backups ---------------- */
export const backups = {
  list: () => request<any[]>("/api/v1/backups", { method: "GET" }),
  create: (databaseId: string) =>
    request<any>("/api/v1/backups", {
      method: "POST",
      body: JSON.stringify({ database_id: databaseId }),
    }),
  restore: (id: string) =>
    request<any>(`/api/v1/backups/${id}/restore`, { method: "POST" }),
};

/* ---------------- Metrics ---------------- */
export const metrics = {
  forDatabase: (databaseId: string) =>
    request<any>(`/api/v1/metrics/databases/${databaseId}`, { method: "GET" }),
};

/* ---------------- Endpoints ---------------- */
export const endpoints = {
  get: (id: string) =>
    request<any>(`/api/v1/endpoints/${id}`, { method: "GET" }),
};

/* ---------------- Auth ---------------- */
export const auth = {
  health: () => request<any>("/health", { method: "GET" }),
};

/**
 * API client for the Singularity backend.
 *
 * All requests go through this module which handles:
 * - Base URL configuration
 * - Auth token injection
 * - Error normalization
 */
import { getSession } from "next-auth/react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function getAuthHeaders(): Promise<HeadersInit> {
  const session = await getSession();
  const token = session?.accessToken;
  if (!token) {
    console.warn("[api] No access token found in session");
    return {};
  }
  return { Authorization: `Bearer ${token}` };
}

function isLikelyExpiredAccessToken(status: number, message: string): boolean {
  if (status !== 401) return false;
  const m = message.toLowerCase();
  return (
    m.includes("invalid") && m.includes("token")
  ) || m.includes("expired");
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  authRetryAttempt = 0,
): Promise<T> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...headers,
      ...(options.headers || {}),
    },
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const message = String(body.detail || res.statusText || "");
    if (
      authRetryAttempt === 0 &&
      typeof window !== "undefined" &&
      isLikelyExpiredAccessToken(res.status, message)
    ) {
      await getSession({ broadcast: true });
      return request(path, options, 1);
    }
    throw new ApiError(res.status, message || res.statusText, body);
  }

  // Handle 204 No Content
  if (res.status === 204) return undefined as T;
  return res.json();
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public body?: any,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export const authApi = {
  googleLogin: (idToken: string) =>
    request<{ access_token: string; refresh_token: string; expires_in: number }>(
      "/api/v1/auth/google",
      { method: "POST", body: JSON.stringify({ id_token: idToken }) },
    ),
  refresh: (refreshToken: string) =>
    request<{ access_token: string; refresh_token: string; expires_in: number }>(
      "/api/v1/auth/refresh",
      { method: "POST", body: JSON.stringify({ refresh_token: refreshToken }) },
    ),
  logout: (refreshToken: string) =>
    request<void>("/api/v1/auth/logout", {
      method: "POST",
      body: JSON.stringify({ refresh_token: refreshToken }),
    }),
};

// ---------------------------------------------------------------------------
// Reports
// ---------------------------------------------------------------------------

export interface ReportMeta {
  id: string;
  title: string | null;
  query: string;
  strength: number;
  created_at: string;
  latest_version: number | null;
  latest_char_count: number | null;
}

export interface VersionContent {
  version_num: number;
  content: string;
  etag: string;
  char_count: number;
}

export interface VersionMeta {
  version_num: number;
  char_count: number;
  patch_instruction: string | null;
  created_at: string;
}

export const reportsApi = {
  list: (cursor?: string, limit = 20) =>
    request<{ items: ReportMeta[]; next_cursor: string | null }>(
      `/api/v1/reports?${cursor ? `cursor=${cursor}&` : ""}limit=${limit}`,
    ),
  get: (id: string) =>
    request<ReportMeta>(`/api/v1/reports/${id}`),
  delete: (id: string) =>
    request<void>(`/api/v1/reports/${id}`, { method: "DELETE" }),
  getVersions: (id: string) =>
    request<{ report_id: string; versions: VersionMeta[] }>(
      `/api/v1/reports/${id}/versions`,
    ),
  getVersionContent: (id: string, version: number) =>
    request<VersionContent>(`/api/v1/reports/${id}/versions/${version}`),
  patch: (id: string, version: number, data: {
    selected_text: string;
    instruction: string;
    if_match: string;
  }) =>
    request<{ new_version_num: number; etag: string; char_count: number }>(
      `/api/v1/reports/${id}/versions/${version}/patch`,
      { method: "POST", body: JSON.stringify(data) },
    ),
  exportUrl: (id: string, version: number, format: "md" | "html" = "md") =>
    `${API_BASE}/api/v1/reports/${id}/versions/${version}/export?format=${format}`,
};

// ---------------------------------------------------------------------------
// Research Jobs
// ---------------------------------------------------------------------------

export interface JobResponse {
  job_id: string;
  report_id: string;
  status: string;
  current_phase: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  error_detail: string | null;
}

export const jobsApi = {
  create: (query: string, strength = 5, idempotencyKey?: string) =>
    request<JobResponse>("/api/v1/research/jobs", {
      method: "POST",
      body: JSON.stringify({ query, strength, idempotency_key: idempotencyKey }),
    }),
  get: (id: string) =>
    request<JobResponse>(`/api/v1/research/jobs/${id}`),
  cancel: (id: string) =>
    request<{ job_id: string; status: string }>(
      `/api/v1/research/jobs/${id}/cancel`,
      { method: "POST" },
    ),
  eventsUrl: (id: string, token?: string) => {
    const base = `${API_BASE}/api/v1/research/jobs/${id}/events`;
    return token ? `${base}?token=${token}` : base;
  },
};

// ---------------------------------------------------------------------------
// Threads / Chat
// ---------------------------------------------------------------------------

export interface ThreadResponse {
  id: string;
  report_id: string | null;
  pinned_version_num: number | null;
  created_at: string;
}

export interface MessageResponse {
  id: string;
  role: string;
  content: string;
  token_count: number | null;
  created_at: string;
}

export const threadsApi = {
  create: (reportId?: string, pinnedVersion?: number) =>
    request<ThreadResponse>("/api/v1/threads", {
      method: "POST",
      body: JSON.stringify({
        report_id: reportId || null,
        pinned_version: pinnedVersion || null,
      }),
    }),
  list: (limit = 20) =>
    request<ThreadResponse[]>(`/api/v1/threads?limit=${limit}`),
  get: (id: string) =>
    request<{ thread: ThreadResponse; messages: MessageResponse[] }>(
      `/api/v1/threads/${id}`,
    ),
  delete: (id: string) =>
    request<void>(`/api/v1/threads/${id}`, { method: "DELETE" }),
  sendMessageUrl: (id: string) =>
    `${API_BASE}/api/v1/threads/${id}/messages`,
};

// ---------------------------------------------------------------------------
// Users / Stats
// ---------------------------------------------------------------------------

export interface UsageStats {
  total_reports: number;
  total_tokens: number;
  /** Backend uses Decimal; JSON may be a string. */
  total_cost_usd: number | string;
  reports_this_week: number;
  tokens_today: number;
  tokens_remaining_today: number;
  streak_days: number;
  avg_report_strength: number;
  favorite_model: string | null;
  most_active_hour: number | null;
}

export interface UsageSeries {
  series: { date: string; tokens: number; cost_usd: number | string; reports: number }[];
  total_tokens: number;
  total_cost_usd: number | string;
}

export const usersApi = {
  me: () =>
    request<{
      id: string;
      email: string;
      name: string | null;
      avatar_url: string | null;
      created_at: string;
      daily_token_budget: number;
    }>("/api/v1/users/me"),
  stats: () =>
    request<UsageStats>("/api/v1/users/me/stats"),
  usage: (range: "7d" | "30d" | "90d" = "30d") =>
    request<UsageSeries>(`/api/v1/users/me/usage?range=${range}`),
  models: () =>
    request<{ breakdown: { model: string; tokens: number; cost_usd: number; pct: number }[] }>(
      "/api/v1/users/me/usage/models",
    ),
  devices: () =>
    request<{
      devices: { device_type: string; count: number }[];
      os: { os: string; count: number }[];
      browsers: { browser: string; count: number }[];
    }>("/api/v1/users/me/usage/devices"),
};

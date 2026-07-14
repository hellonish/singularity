import { authFetch } from '@/lib/auth';

export interface Chat {
  id: string;
  report_id: string | null;
  provider_credential_id: string | null;
  title: string | null;
  status: string;
  last_message_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  chat_id: string;
  sequence: number;
  role: 'system' | 'user' | 'assistant' | 'tool';
  content: string;
  created_at: string;
  /** Client-only: true while an optimistic assistant turn is waiting for its first token. */
  pending?: boolean;
}

export interface Report {
  id: string;
  title: string | null;
  status: string;
  source: string | null;
  created_at: string;
  updated_at: string;
}

export interface ResearchRun {
  id: string;
  report_id: string | null;
  query: string;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
  started_at: string | null;
  finished_at: string | null;
  error_message: string | null;
  run_data: Record<string, unknown>;
}

export interface ProviderCredential {
  id: string;
  provider: 'groq' | 'deepseek' | 'openrouter';
  label: string | null;
  key_fingerprint: string;
  default_model_id: string | null;
  status: 'active' | 'disabled';
  created_at: string;
  updated_at: string;
}

export interface AvailableModel {
  id: string;
  owned_by: string | null;
  supports_research: boolean;
}

export interface ProviderCredentialSelection {
  credential_id: string | null;
}

export interface SSEEvent {
  event: string;
  data: Record<string, unknown>;
  id?: string;
}

export class ApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

// FastAPI's error body carries `detail`, which is a plain string for
// HTTPExceptions but an array of `{loc, msg, type}` objects for 422 request
// validation errors. Rendering the raw value yields "[object Object]", so
// normalize every shape down to a human-readable string here.
function detailToMessage(detail: unknown, status: number): string {
  if (typeof detail === 'string' && detail) return detail;
  // Some endpoints raise HTTPException with a structured detail object carrying
  // a ready-to-show `message` (e.g. the research free-tier guard). Prefer it.
  if (detail && typeof detail === 'object' && !Array.isArray(detail) && 'message' in detail) {
    const { message } = detail as { message: unknown };
    if (typeof message === 'string' && message) return message;
  }
  if (Array.isArray(detail)) {
    const parts = detail
      .map((item) => {
        if (!item || typeof item !== 'object' || !('msg' in item)) return null;
        const { msg, loc } = item as { msg: unknown; loc?: unknown };
        // Include the failing field path (e.g. "body.query") so a 422 names
        // exactly which field the request got wrong, not just the reason.
        const field = Array.isArray(loc) ? loc.join('.') : null;
        return field ? `${field}: ${String(msg)}` : String(msg);
      })
      .filter((msg): msg is string => Boolean(msg));
    if (parts.length) return parts.join('; ');
  }
  return `Request failed (${status})`;
}

async function errorMessage(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    return detailToMessage(body.detail, response.status);
  } catch {
    return `Request failed (${response.status})`;
  }
}

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await authFetch(path, init);
  if (!response.ok) throw new ApiError(response.status, await errorMessage(response));
  return response.json() as Promise<T>;
}

export async function requestSSE(path: string, init: RequestInit, onEvent: (event: SSEEvent) => void): Promise<void> {
  const response = await authFetch(path, init);
  if (!response.ok) throw new ApiError(response.status, await errorMessage(response));
  if (!response.body) throw new Error('The server opened an empty event stream.');
  await consumeSSE(response.body, onEvent);
}

/** Parse the SSE response body used by the API, including partial network chunks. */
export async function consumeSSE(stream: ReadableStream<Uint8Array>, onEvent: (event: SSEEvent) => void): Promise<void> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  const dispatch = (frame: string) => {
    let event = 'message';
    let id: string | undefined;
    const data: string[] = [];
    for (const line of frame.split(/\r?\n/)) {
      if (line.startsWith('event:')) event = line.slice(6).trim();
      else if (line.startsWith('id:')) id = line.slice(3).trim();
      else if (line.startsWith('data:')) data.push(line.slice(5).trimStart());
    }
    if (!data.length) return;
    try {
      onEvent({ event, id, data: JSON.parse(data.join('\n')) as Record<string, unknown> });
    } catch {
      // A malformed event cannot be acted on safely. Keep the live stream open
      // for a later terminal error instead of treating it as a valid response.
    }
  };

  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });
    const frames = buffer.split(/\r?\n\r?\n/);
    buffer = frames.pop() || '';
    frames.forEach(dispatch);
    if (done) break;
  }
  if (buffer.trim()) dispatch(buffer);
}

export const api = {
  listChats: () => request<Chat[]>('/chats'),
  createChat: (body: { title?: string; report_id?: string; provider_credential_id: string; model_id?: string }) =>
    request<Chat>('/chats', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }),
  deleteChat: (chatId: string) => request<Chat>(`/chats/${chatId}`, { method: 'DELETE' }),
  listMessages: (chatId: string) => request<Message[]>(`/chats/${chatId}/messages`),
  streamMessage: (
    chatId: string,
    content: string,
    effort: 'instant' | 'medium' | 'high' | 'ultra',
    onEvent: (event: SSEEvent) => void,
  ) => requestSSE(
    `/chats/${chatId}/messages/stream`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content, role: 'user', message_data: { effort } }),
    },
    onEvent,
  ),
  listReports: () => request<Report[]>('/reports'),
  deleteReport: (reportId: string) => request<Report>(`/reports/${reportId}`, { method: 'DELETE' }),
  getReportContent: async (reportId: string) => {
    const versions = await request<Array<{ id: string }>>(`/reports/${reportId}/versions`);
    if (!versions.length) return '';
    const response = await authFetch(`/reports/${reportId}/versions/${versions.at(-1)!.id}/content`);
    if (!response.ok) throw new ApiError(response.status, await errorMessage(response));
    return response.text();
  },
  listRuns: () => request<ResearchRun[]>('/research/runs'),
  createRun: (body: { query: string; title?: string; provider_credential_id: string; model_id?: string; strength: number }) =>
    request<ResearchRun>('/research/runs', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }),
  cancelRun: (runId: string) => request<ResearchRun>(`/research/runs/${runId}/cancel`, { method: 'POST' }),
  getRun: (runId: string) => request<ResearchRun>(`/research/runs/${runId}`),
  listCredentials: () => request<ProviderCredential[]>('/llm/credentials'),
  getCredentialSelection: () => request<ProviderCredentialSelection>('/llm/selection'),
  setCredentialSelection: (credentialId: string | null) =>
    request<ProviderCredentialSelection>('/llm/selection', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ credential_id: credentialId }) }),
  listCredentialModels: (credentialId: string) => request<AvailableModel[]>(`/llm/credentials/${credentialId}/models`),
  createCredential: (body: { provider: ProviderCredential['provider']; api_key: string; label?: string; default_model_id?: string }) =>
    request<ProviderCredential>('/llm/credentials', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }),
  updateCredential: (id: string, body: { status?: 'active' | 'disabled'; label?: string; default_model_id?: string }) =>
    request<ProviderCredential>(`/llm/credentials/${id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }),
};

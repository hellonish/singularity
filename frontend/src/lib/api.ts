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

/** One live step the agent reported while a turn was still thinking. */
export interface ProgressStep {
  /** Engine progress_kind, e.g. 'routing' | 'tool_start' | 'tool_completed'. */
  kind: string;
  /** Humanized, user-facing description of the step. */
  label: string;
  /** Wall time the underlying tool call took, when the engine reports it. */
  elapsedSeconds?: number;
  /** True once the step's underlying action finished (success or failure). */
  done: boolean;
  /** True when the step represents a failure the model had to recover from. */
  failed: boolean;
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
  /** Client-only: live agent progress steps streamed before the answer began. */
  progress?: ProgressStep[];
}

/** Raw engine tool labels look like: `web_search(query='foo bar', arguments={...})`. */
const TOOL_LABEL = /^(\w+)\(query=(['"])([\s\S]*?)\2/;

/** Turn one engine progress event into a user-facing step description.
 *
 * The engine speaks in tool-call syntax and budget notes; this maps the parts a
 * reader cares about (which tool, what query, how many sources) into a sentence,
 * and falls back to the raw message for kinds we do not specifically dress up.
 */
export function humanizeProgress(kind: string, message: string): string {
  const toolName = (raw: string) => raw.replace(/_/g, ' ').replace(/\bweb search\b/i, 'web search');
  const match = message.match(TOOL_LABEL);
  const query = match?.[3]?.trim();
  const tool = match?.[1];
  // `tool_completed` labels carry a trailing "— N source(s)" suffix.
  const sources = message.match(/—\s*(\d+)\s*source/);

  switch (kind) {
    case 'routing':
      return message;
    case 'agent_budget':
      return 'Planning the approach';
    case 'tool_planning_start':
      return 'Deciding what to look up';
    case 'tool_start':
      if (tool === 'web_search' && query) return `Searching the web for “${query}”`;
      if (query) return `Running ${toolName(tool ?? 'a tool')} for “${query}”`;
      return `Running ${toolName(tool ?? 'a tool')}`;
    case 'tool_completed':
      if (tool === 'web_search' && sources) return `Found ${sources[1]} source${sources[1] === '1' ? '' : 's'} for “${query ?? '…'}”`;
      if (sources) return `${toolName(tool ?? 'Tool')} returned ${sources[1]} source${sources[1] === '1' ? '' : 's'}`;
      return `Finished ${toolName(tool ?? 'a tool')}`;
    case 'tool_failed':
      return query ? `Search for “${query}” didn’t return results` : `${toolName(tool ?? 'A tool')} didn’t return results`;
    default:
      return message;
  }
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
  preparation_id: string | null;
  query: string;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
  started_at: string | null;
  finished_at: string | null;
  error_message: string | null;
  run_data: Record<string, unknown>;
}

export interface ClarificationQuestion {
  question_id: string;
  text: string;
  reason: string;
}

export interface ResearchBrief {
  refined_objective: string;
  plan_points: string[];
  questions: ClarificationQuestion[];
  must_haves: string[];
  deliverable: string;
  assumptions: string[];
  entity_scope: Record<string, unknown>;
}

export interface ResearchPreparation {
  id: string;
  query: string;
  approval_mode: 'ask' | 'auto';
  status: 'draft' | 'awaiting_input' | 'ready' | 'started' | 'cancelled' | 'failed';
  model_id: string | null;
  strength: number;
  current_question_index: number;
  plan_data: Partial<ResearchBrief> & Record<string, unknown>;
  answers: Record<string, string>;
  final_brief: Partial<ResearchBrief> & Record<string, unknown>;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface ResearchPreparationResult {
  preparation: ResearchPreparation;
  run: ResearchRun | null;
}

/** The six pipeline phases shown in the Research Run rail, in order. */
export const RESEARCH_PHASES = [
  { key: 'scoping', label: 'Scoping', cap: 'Define the objective' },
  { key: 'planning', label: 'Planning', cap: 'Decompose workstreams' },
  { key: 'researching', label: 'Researching', cap: 'Gather & run tools' },
  { key: 'reviewing', label: 'Reviewing', cap: 'Verify every claim' },
  { key: 'writing', label: 'Writing', cap: 'Compose the report' },
  { key: 'report', label: 'Report ready', cap: 'Cited & delivered' },
] as const;

export type ResearchPhaseKey = (typeof RESEARCH_PHASES)[number]['key'];
export type PhaseState = 'queued' | 'live' | 'done';

/** One live feed item derived from a `research.progress` event. Discriminated by
 * `kind` — each maps to exactly one Research Run feed component. */
export type RunFeedItem =
  | { id: string; kind: 'phase'; label: string }
  | { id: string; kind: 'thought'; text: string }
  | { id: string; kind: 'scope'; objective: string; mustHaves: string[]; deliverable: string }
  | { id: string; kind: 'research_plan'; points: string[] }
  | { id: string; kind: 'agent_dispatch'; nodeId: string; question: string }
  | { id: string; kind: 'tool_call'; tool: string; nodeId?: string; status: string; query?: string; sourceCount?: number; elapsedSeconds?: number; running: boolean; failed: boolean }
  | { id: string; kind: 'source_added'; title: string; url: string; sourceType: string }
  | { id: string; kind: 'section_written'; title: string };

/** Derived counters for the Live telemetry tiles. Sandboxes stays 0 until the
 * workflow emits real container/sandbox events; tokens is a display estimate. */
export interface RunTelemetry {
  sources: number;
  toolCalls: number;
  sandboxes: number;
  tokens: number;
}

/** Everything the Research Run view needs for one run, accumulated from its
 * event stream. `activity` mirrors the thin summary the report view still uses. */
export interface RunProgress {
  feed: RunFeedItem[];
  telemetry: RunTelemetry;
  /** phase key -> state, driving the pipeline rail. */
  phases: Record<ResearchPhaseKey, PhaseState>;
  /** The phase currently live, for the status kicker. */
  currentPhase: ResearchPhaseKey;
  activity: { phase?: string; status?: string; message?: string; error?: string };
}

/** Raw shape of a `research.progress` SSE payload (all fields optional; `kind`
 * discriminates). The backend always includes `kind`, `phase`, `status`. */
export interface ResearchProgressPayload {
  kind?: string;
  phase?: string;
  status?: string;
  message?: string;
  node_id?: string;
  question?: string;
  tool_name?: string;
  source_count?: number;
  elapsed_seconds?: number;
  title?: string;
  url?: string;
  source_type?: string;
  objective?: string;
  must_haves?: string[];
  deliverable?: string;
  plan_points?: string[];
  section_title?: string;
  error?: string;
  cycle?: number;
  [key: string]: unknown;
}

/** Map a backend `phase` string to a rail phase key. Scoping and planning both
 * arrive under the "planning" backend phase; the scope event promotes to
 * scoping, everything else after it is planning. */
export function railPhaseKey(backendPhase: string | undefined, kind: string | undefined): ResearchPhaseKey {
  if (kind === 'scope') return 'scoping';
  switch (backendPhase) {
    case 'planning': return 'planning';
    case 'researching': return 'researching';
    case 'reviewing': return 'reviewing';
    case 'writing': return 'writing';
    default: return 'scoping';
  }
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
  createPreparation: (body: { query: string; approval_mode: 'ask' | 'auto'; provider_credential_id: string; model_id?: string; strength: number }) =>
    request<ResearchPreparationResult>('/research/preparations', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }),
  getPreparation: (preparationId: string) => request<ResearchPreparation>(`/research/preparations/${preparationId}`),
  answerPreparation: (preparationId: string, questionId: string, answer: string) =>
    request<ResearchPreparation>(`/research/preparations/${preparationId}/answers`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question_id: questionId, answer }) }),
  startPreparation: (preparationId: string) =>
    request<ResearchRun>(`/research/preparations/${preparationId}/start`, { method: 'POST' }),
  cancelPreparation: (preparationId: string) =>
    request<ResearchPreparation>(`/research/preparations/${preparationId}`, { method: 'DELETE' }),
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

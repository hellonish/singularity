'use client';

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { api, ApiError, AvailableModel, Chat, humanizeProgress, Message, ProviderCredential, Report, ResearchProgressPayload, ResearchRun, RunProgress, requestSSE, SSEEvent } from '@/lib/api';
import { emptyRunProgress, reduceProgress } from '@/lib/research-feed';

type RunActivity = { phase?: string; status?: string; message?: string; error?: string };

function userErrorMessage(cause: unknown, fallback: string): string {
  return cause instanceof Error && cause.message ? cause.message : fallback;
}

/**
 * Map a failed research start to a message safe to show an end user.
 *
 * The raw server detail (e.g. a 422's "body.query: Field required") is a
 * developer diagnostic, so it goes to the console, never the banner. Users see
 * a friendly, class-based line keyed on HTTP status.
 */
function researchErrorMessage(cause: unknown): string {
  if (cause instanceof ApiError) {
    // Log the precise cause for developers; keep it out of the UI.
    console.error('startResearch failed', cause.status, cause.message);
    switch (cause.status) {
      case 401:
        return 'Your session expired. Please sign in again.';
      case 422:
        // 422 here is an application guard (e.g. a free-tier provider that
        // can't sustain a run), not a form error. The server sends a
        // ready-to-show reason in the message, so surface it directly.
        return cause.message || 'Could not start research. Please try again.';
      case 429:
        return "You've started several research runs recently. Please wait a moment and try again.";
      case 503:
        return 'Research is temporarily unavailable. Please try again in a moment.';
      default:
        return cause.status >= 500
          ? 'Something went wrong on our end. Please try again in a moment.'
          : 'Could not start research. Please try again.';
    }
  }
  console.error('startResearch failed', cause);
  return 'Could not start research. Please try again.';
}

interface WorkspaceData {
  chats: Chat[];
  reports: Report[];
  runs: ResearchRun[];
  credentials: ProviderCredential[];
  availableModels: AvailableModel[];
  modelsLoading: boolean;
  messages: Record<string, Message[]>;
  /** Ids of chats with a reply stream currently in flight. */
  streamingChatIds: string[];
  reportContent: Record<string, string>;
  runActivity: Record<string, RunActivity>;
  /** Rich per-run progress (feed, telemetry, pipeline) for the Research Run view. */
  runProgress: Record<string, RunProgress>;
  loading: boolean;
  error: string | null;
  activeCredential: ProviderCredential | null;
  refresh: () => Promise<void>;
  loadMessages: (chatId: string) => Promise<void>;
  loadReport: (reportId: string) => Promise<void>;
  createChat: (reportId?: string, modelId?: string) => Promise<Chat>;
  createAndSendChat: (content: string, reportId?: string, modelId?: string, effort?: 'instant' | 'medium' | 'high' | 'ultra') => Promise<Chat>;
  sendChat: (chatId: string, content: string, effort?: 'instant' | 'medium' | 'high' | 'ultra') => Promise<void>;
  deleteChat: (chatId: string) => Promise<void>;
  deleteReport: (reportId: string) => Promise<void>;
  startResearch: (query: string, strength: number, modelId?: string) => Promise<ResearchRun>;
  cancelResearch: (runId: string) => Promise<void>;
  selectCredential: (credentialId: string | null) => Promise<void>;
  saveCredential: (provider: ProviderCredential['provider'], apiKey: string) => Promise<ProviderCredential>;
  setDefaultModel: (modelId: string) => Promise<void>;
  disableCredential: (credentialId: string) => Promise<void>;
  clearError: () => void;
}

const WorkspaceContext = createContext<WorkspaceData | null>(null);

const terminalResearchEvents = new Set(['research.completed', 'research.failed', 'research.cancelled']);

function shortTitle(content: string): string {
  return content.trim().replace(/\s+/g, ' ').slice(0, 80);
}

export function WorkspaceProvider({ children }: { children: React.ReactNode }) {
  const [chats, setChats] = useState<Chat[]>([]);
  const [reports, setReports] = useState<Report[]>([]);
  const [runs, setRuns] = useState<ResearchRun[]>([]);
  const [credentials, setCredentials] = useState<ProviderCredential[]>([]);
  const [selectedCredentialId, setSelectedCredentialId] = useState<string | null>(null);
  const [availableModels, setAvailableModels] = useState<AvailableModel[]>([]);
  const [modelsLoading, setModelsLoading] = useState(false);
  const [messages, setMessages] = useState<Record<string, Message[]>>({});
  const [reportContent, setReportContent] = useState<Record<string, string>>({});
  const [runActivity, setRunActivity] = useState<Record<string, RunActivity>>({});
  const [runProgress, setRunProgress] = useState<Record<string, RunProgress>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const runControllers = useRef(new Map<string, AbortController>());
  // Chats with an in-flight message stream. While a chat is in here its
  // optimistic messages are authoritative: a concurrent loadMessages must not
  // replace them with the (still incomplete) persisted turns. The ref is the
  // synchronous guard; the state mirror lets the UI react (e.g. lock the send
  // button for a chat that is already answering).
  const streamingChats = useRef(new Set<string>());
  const [streamingChatIds, setStreamingChatIds] = useState<string[]>([]);

  const activeCredential = useMemo(
    () => credentials.find((credential) => credential.id === selectedCredentialId && credential.status === 'active')
      ?? credentials.find((credential) => credential.status === 'active')
      ?? null,
    [credentials, selectedCredentialId],
  );

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [nextReports, nextChats, nextCredentials, nextRuns, selection] = await Promise.all([
        api.listReports(), api.listChats(), api.listCredentials(), api.listRuns(), api.getCredentialSelection(),
      ]);
      setReports(nextReports);
      setChats(nextChats);
      setCredentials(nextCredentials);
      setSelectedCredentialId(selection.credential_id);
      setRuns(nextRuns);
      setError(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not load your workspace.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => { void refresh(); }, 0);
    return () => window.clearTimeout(timer);
  }, [refresh]);
  useEffect(() => () => runControllers.current.forEach((controller) => controller.abort()), []);

  const activeCredentialId = activeCredential?.id;

  useEffect(() => {
    if (!activeCredentialId) {
      const clearModels = window.setTimeout(() => {
        setAvailableModels([]);
        setModelsLoading(false);
      }, 0);
      return () => window.clearTimeout(clearModels);
    }
    let cancelled = false;
    const startModelLoad = window.setTimeout(() => {
      setModelsLoading(true);
      void api.listCredentialModels(activeCredentialId)
        .then((models) => {
          if (!cancelled) {
            setAvailableModels(models);
            setError(null);
          }
        })
        .catch((cause) => {
          if (!cancelled) {
            setAvailableModels([]);
            setError(cause instanceof Error ? cause.message : 'Could not load models for this provider.');
          }
        })
        .finally(() => {
          if (!cancelled) setModelsLoading(false);
        });
    }, 0);
    return () => { cancelled = true; window.clearTimeout(startModelLoad); };
  }, [activeCredentialId]);

  const loadMessages = useCallback(async (chatId: string) => {
    if (streamingChats.current.has(chatId)) return;
    try {
      const turns = await api.listMessages(chatId);
      // The stream may have started while the request was in flight; its
      // optimistic view stays authoritative until the stream settles.
      if (streamingChats.current.has(chatId)) return;
      setMessages((current) => ({ ...current, [chatId]: turns }));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not load this chat.');
    }
  }, []);

  const loadReport = useCallback(async (reportId: string) => {
    try {
      const content = await api.getReportContent(reportId);
      setReportContent((current) => ({ ...current, [reportId]: content }));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not load this report.');
    }
  }, []);

  const sendChat = useCallback(async (
    chatId: string,
    content: string,
    effort: 'instant' | 'medium' | 'high' | 'ultra' = 'medium',
  ) => {
    const placeholderId = `streaming-${Date.now()}`;
    const userId = `sending-${Date.now()}`;
    streamingChats.current.add(chatId);
    setStreamingChatIds(Array.from(streamingChats.current));
    setMessages((current) => ({
      ...current,
      [chatId]: [...(current[chatId] ?? []),
        { id: userId, chat_id: chatId, sequence: Number.MAX_SAFE_INTEGER - 1, role: 'user', content, created_at: new Date().toISOString() },
        { id: placeholderId, chat_id: chatId, sequence: Number.MAX_SAFE_INTEGER, role: 'assistant', content: '', created_at: new Date().toISOString(), pending: true },
      ],
    }));

    const updateAssistant = (next: string, done = false) => {
      setMessages((current) => ({ ...current, [chatId]: (current[chatId] ?? []).map((message) =>
        message.id === placeholderId ? { ...message, content: next, pending: false, ...(done ? { id: `completed-${Date.now()}` } : {}) } : message,
      ) }));
    };

    try {
      await api.streamMessage(chatId, content, effort, (event: SSEEvent) => {
        if (event.event === 'message.progress') {
          const kind = typeof event.data.kind === 'string' ? event.data.kind : '';
          const raw = typeof event.data.message === 'string' ? event.data.message : '';
          const elapsedSeconds = typeof event.data.elapsed_seconds === 'number' ? event.data.elapsed_seconds : undefined;
          const label = humanizeProgress(kind, raw);
          const failed = kind === 'tool_failed';
          const done = kind === 'tool_completed' || failed;
          setMessages((current) => ({ ...current, [chatId]: (current[chatId] ?? []).map((message) => {
            if (message.id !== placeholderId) return message;
            const steps = [...(message.progress ?? [])];
            // A tool_completed/failed event closes out the pending tool_start for
            // the same query instead of adding a second, near-duplicate line.
            if (done) {
              const openIndex = steps.findIndex((step) => step.kind === 'tool_start' && !step.done);
              if (openIndex !== -1) {
                steps[openIndex] = { ...steps[openIndex], kind, label, elapsedSeconds, done: true, failed };
                return { ...message, progress: steps };
              }
            }
            steps.push({ kind, label, elapsedSeconds, done, failed });
            return { ...message, progress: steps };
          }) }));
        }
        if (event.event === 'message.delta') {
          const delta = typeof event.data.delta === 'string' ? event.data.delta : '';
          setMessages((current) => ({ ...current, [chatId]: (current[chatId] ?? []).map((message) =>
            message.id === placeholderId ? { ...message, content: message.content + delta, pending: false } : message,
          ) }));
        }
        if (event.event === 'message.completed') {
          updateAssistant(typeof event.data.content === 'string' ? event.data.content : '', true);
        }
        if (event.event === 'chat.title') {
          const title = typeof event.data.title === 'string' ? event.data.title : null;
          if (title) setChats((current) => current.map((chat) => chat.id === chatId ? { ...chat, title } : chat));
        }
        if (event.event === 'message.error') {
          const message = typeof event.data.message === 'string' ? event.data.message : 'The model could not complete this reply.';
          updateAssistant(message, true);
          setError(message);
        }
      });
    } catch (cause) {
      const message = userErrorMessage(cause, 'The message could not be sent.');
      updateAssistant(message, true);
      setError(message);
    } finally {
      // Reconcile with the server only after the stream settles: swap the
      // optimistic turns for the persisted ones and refresh chat ordering.
      streamingChats.current.delete(chatId);
      setStreamingChatIds(Array.from(streamingChats.current));
      void loadMessages(chatId);
      void api.listChats().then(setChats).catch((cause) => {
        setError(userErrorMessage(cause, 'Could not refresh your chats.'));
      });
    }
  }, [loadMessages]);

  const deleteChat = useCallback(async (chatId: string) => {
    try {
      await api.deleteChat(chatId);
      setChats((current) => current.filter((chat) => chat.id !== chatId));
    } catch (cause) {
      setError(userErrorMessage(cause, 'Could not delete this chat.'));
      throw cause;
    }
  }, []);

  const deleteReport = useCallback(async (reportId: string) => {
    try {
      await api.deleteReport(reportId);
      setReports((current) => current.filter((report) => report.id !== reportId));
    } catch (cause) {
      setError(userErrorMessage(cause, 'Could not delete this report.'));
      throw cause;
    }
  }, []);

  const requireCredential = useCallback(() => {
    if (!activeCredential) {
      const error = new Error('Add an active provider key in Settings before starting Chat or Research.');
      setError(error.message);
      throw error;
    }
    return activeCredential;
  }, [activeCredential]);

  const createChat = useCallback(async (reportId?: string, modelId?: string) => {
    const credential = requireCredential();
    try {
      // No client title: the backend names the chat from the first exchange and
      // announces it through the stream's `chat.title` event.
      const chat = await api.createChat({
        report_id: reportId, provider_credential_id: credential.id,
        model_id: modelId ?? credential.default_model_id ?? undefined,
      });
      setChats((current) => [chat, ...current]);
      return chat;
    } catch (cause) {
      setError(userErrorMessage(cause, 'Could not create a new chat.'));
      throw cause;
    }
  }, [requireCredential]);

  const createAndSendChat = useCallback(async (
    content: string,
    reportId?: string,
    modelId?: string,
    effort: 'instant' | 'medium' | 'high' | 'ultra' = 'medium',
  ) => {
    const chat = await createChat(reportId, modelId);
    // Stream in the background so the caller can open the chat view and watch
    // the reply arrive token by token; sendChat reports its own errors.
    void sendChat(chat.id, content, effort);
    return chat;
  }, [createChat, sendChat]);

  const streamResearch = useCallback(async (run: ResearchRun) => {
    const controller = new AbortController();
    runControllers.current.set(run.id, controller);
    let cursor: string | undefined;
    let terminal = false;
    try {
      while (!terminal && !controller.signal.aborted) {
        const headers = new Headers();
        if (cursor) headers.set('Last-Event-ID', cursor);
        try {
          await requestSSE(`/research/runs/${run.id}/events`, { headers, signal: controller.signal }, (event) => {
            if (event.id) cursor = event.id;
            if (event.event === 'research.heartbeat') return;
            const status = typeof event.data.status === 'string' ? event.data.status : undefined;
            // Fold progress events into the rich per-run feed/telemetry/pipeline.
            // Phase-node events (research.phase) and progress events both name a
            // phase, so both advance the rail; only research.progress carries a
            // feed-worthy `kind`.
            if (event.event === 'research.progress' || event.event === 'research.phase') {
              setRunProgress((current) => ({
                ...current,
                [run.id]: reduceProgress(current[run.id] ?? emptyRunProgress(), event.data as ResearchProgressPayload),
              }));
            }
            setRunActivity((current) => ({ ...current, [run.id]: {
              phase: typeof event.data.phase === 'string' ? event.data.phase : current[run.id]?.phase,
              status: typeof event.data.status === 'string' ? event.data.status : current[run.id]?.status,
              message: typeof event.data.message === 'string' ? event.data.message : current[run.id]?.message,
              error: typeof event.data.error === 'string' ? event.data.error : undefined,
            } }));
            setRuns((current) => current.map((item) => item.id === run.id ? { ...item, status: (status ?? item.status) as ResearchRun['status'] } : item));
            if (event.event === 'research.failed') {
              setError(typeof event.data.error === 'string' ? event.data.error : typeof event.data.message === 'string' ? event.data.message : 'Research failed.');
            }
            terminal = terminalResearchEvents.has(event.event);
          });
        } catch (cause) {
          if (controller.signal.aborted) return;
          setError(cause instanceof Error ? cause.message : 'Lost the research progress stream. Retrying…');
        }
        if (!terminal && !controller.signal.aborted) await new Promise((resolve) => setTimeout(resolve, 1000));
      }
      const finalRun = await api.getRun(run.id);
      setRuns((current) => current.map((item) => item.id === run.id ? finalRun : item));
      // On success, mark the whole pipeline done so the rail and status kicker
      // settle on "Report ready" even though no phase event names that stage.
      if (finalRun.status === 'completed') {
        setRunProgress((current) => {
          const existing = current[run.id] ?? emptyRunProgress();
          return { ...current, [run.id]: {
            ...existing,
            currentPhase: 'report',
            phases: { scoping: 'done', planning: 'done', researching: 'done', reviewing: 'done', writing: 'done', report: 'done' },
          } };
        });
      }
      if (finalRun.status === 'failed') setError(finalRun.error_message || 'Research failed.');
      if (finalRun.report_id) {
        await loadReport(finalRun.report_id);
        const report = await api.listReports();
        setReports(report);
      }
    } finally {
      runControllers.current.delete(run.id);
    }
  }, [loadReport]);

  const startResearch = useCallback(async (query: string, strength: number, modelId?: string) => {
    const credential = requireCredential();
    try {
      const run = await api.createRun({ query, title: shortTitle(query), provider_credential_id: credential.id, model_id: modelId ?? credential.default_model_id ?? undefined, strength });
      setRuns((current) => [run, ...current]);
      setReports((current) => run.report_id ? [{ id: run.report_id, title: shortTitle(query), status: 'processing', source: 'research', created_at: new Date().toISOString(), updated_at: new Date().toISOString() }, ...current] : current);
      void streamResearch(run);
      return run;
    } catch (cause) {
      const message = researchErrorMessage(cause);
      setError(message);
      throw new Error(message);
    }
  }, [requireCredential, streamResearch]);

  // Resume progress streams for any run that is still active but has no live
  // stream — e.g. after a page reload, or a run started in another tab. Without
  // this, the Research Run view would sit empty for an in-flight run.
  useEffect(() => {
    for (const run of runs) {
      if (['completed', 'failed', 'cancelled'].includes(run.status)) continue;
      if (runControllers.current.has(run.id)) continue;
      void streamResearch(run);
    }
  }, [runs, streamResearch]);

  const cancelResearch = useCallback(async (runId: string) => {
    try {
      const run = await api.cancelRun(runId);
      runControllers.current.get(runId)?.abort();
      setRuns((current) => current.map((item) => item.id === runId ? run : item));
    } catch (cause) {
      setError(userErrorMessage(cause, 'Could not cancel this research run.'));
      throw cause;
    }
  }, []);

  const selectCredential = useCallback(async (credentialId: string | null) => {
    try {
      const selection = await api.setCredentialSelection(credentialId);
      setSelectedCredentialId(selection.credential_id);
    } catch (cause) {
      setError(userErrorMessage(cause, 'Could not select this provider key.'));
      throw cause;
    }
  }, []);

  const saveCredential = useCallback(async (provider: ProviderCredential['provider'], apiKey: string) => {
    try {
      const credential = await api.createCredential({ provider, api_key: apiKey, label: `${provider} key` });
      setCredentials((current) => [credential, ...current]);
      const selection = await api.setCredentialSelection(credential.id);
      setSelectedCredentialId(selection.credential_id);
      return credential;
    } catch (cause) {
      setError(userErrorMessage(cause, 'Could not save this provider key.'));
      throw cause;
    }
  }, []);

  const setDefaultModel = useCallback(async (modelId: string) => {
    const credential = activeCredential;
    if (!credential) {
      const error = new Error('Select a provider key before choosing a model.');
      setError(error.message);
      throw error;
    }
    try {
      const updated = await api.updateCredential(credential.id, { default_model_id: modelId });
      setCredentials((current) => current.map((item) => item.id === updated.id ? updated : item));
    } catch (cause) {
      setError(userErrorMessage(cause, 'Could not choose this model.'));
      throw cause;
    }
  }, [activeCredential]);

  const disableCredential = useCallback(async (credentialId: string) => {
    try {
      const credential = await api.updateCredential(credentialId, { status: 'disabled' });
      setCredentials((current) => current.map((item) => item.id === credential.id ? credential : item));
      if (credential.id === selectedCredentialId) {
        const selection = await api.setCredentialSelection(null);
        setSelectedCredentialId(selection.credential_id);
      }
    } catch (cause) {
      setError(userErrorMessage(cause, 'Could not disable this provider key.'));
      throw cause;
    }
  }, [selectedCredentialId]);

  const clearError = useCallback(() => setError(null), []);

  const value = useMemo<WorkspaceData>(() => ({
    chats, reports, runs, credentials, availableModels, modelsLoading, messages, streamingChatIds, reportContent, runActivity, runProgress, loading, error, activeCredential,
    refresh, loadMessages, loadReport, createChat, createAndSendChat, sendChat, deleteChat, deleteReport, startResearch, cancelResearch, selectCredential, saveCredential, setDefaultModel, disableCredential,
    clearError,
  }), [chats, reports, runs, credentials, availableModels, modelsLoading, messages, streamingChatIds, reportContent, runActivity, runProgress, loading, error, activeCredential, refresh, loadMessages, loadReport, createChat, createAndSendChat, sendChat, deleteChat, deleteReport, startResearch, cancelResearch, selectCredential, saveCredential, setDefaultModel, disableCredential, clearError]);

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}

export function useWorkspace(): WorkspaceData {
  const value = useContext(WorkspaceContext);
  if (!value) throw new Error('useWorkspace must be used inside WorkspaceProvider.');
  return value;
}

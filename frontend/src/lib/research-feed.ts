import {
  PhaseState,
  RESEARCH_PHASES,
  ResearchPhaseKey,
  ResearchProgressPayload,
  RunFeedItem,
  RunProgress,
  railPhaseKey,
} from '@/lib/api';

const PHASE_ORDER: ResearchPhaseKey[] = RESEARCH_PHASES.map((p) => p.key);

/** A fresh, empty progress accumulator for a run before any event arrives. */
export function emptyRunProgress(): RunProgress {
  const phases = Object.fromEntries(
    PHASE_ORDER.map((key, i) => [key, i === 0 ? 'live' : 'queued']),
  ) as Record<ResearchPhaseKey, PhaseState>;
  return {
    feed: [],
    telemetry: { sources: 0, toolCalls: 0, sandboxes: 0, tokens: 0 },
    phases,
    currentPhase: 'scoping',
    activity: {},
  };
}

/** Mark every phase before `key` done, `key` live, the rest queued — a pipeline
 * only advances forward, so reaching a later phase implies earlier ones finished. */
function advancePhases(phases: Record<ResearchPhaseKey, PhaseState>, key: ResearchPhaseKey): Record<ResearchPhaseKey, PhaseState> {
  const target = PHASE_ORDER.indexOf(key);
  const currentMax = PHASE_ORDER.reduce((max, k, i) => (phases[k] !== 'queued' ? i : max), 0);
  // Never regress: a late researching event must not un-complete reviewing.
  const at = Math.max(target, currentMax);
  const next = {} as Record<ResearchPhaseKey, PhaseState>;
  PHASE_ORDER.forEach((k, i) => { next[k] = i < at ? 'done' : i === at ? 'live' : 'queued'; });
  return next;
}

/** A short label for a tool_call feed item's query, pulled from the message. */
function toolQuery(payload: ResearchProgressPayload): string | undefined {
  const message = typeof payload.message === 'string' ? payload.message : '';
  const quoted = message.match(/["“]([^"”]+)["”]/);
  if (quoted) return quoted[1];
  return undefined;
}

let seq = 0;
function nextId(): string { seq += 1; return `rf-${seq}`; }

/** Fold one `research.progress` payload into the run's accumulated progress.
 * Pure apart from the monotonic id counter; returns a new object (never mutates
 * the input) so React state updates stay referentially honest. */
export function reduceProgress(prev: RunProgress, payload: ResearchProgressPayload): RunProgress {
  const kind = typeof payload.kind === 'string' ? payload.kind : 'phase';
  const next: RunProgress = {
    feed: prev.feed,
    telemetry: { ...prev.telemetry },
    phases: prev.phases,
    currentPhase: prev.currentPhase,
    activity: {
      phase: typeof payload.phase === 'string' ? payload.phase : prev.activity.phase,
      status: typeof payload.status === 'string' ? payload.status : prev.activity.status,
      message: typeof payload.message === 'string' ? payload.message : prev.activity.message,
      error: typeof payload.error === 'string' ? payload.error : undefined,
    },
  };

  // Advance the rail for any event that names a phase.
  const railKey = railPhaseKey(typeof payload.phase === 'string' ? payload.phase : undefined, kind);
  next.phases = advancePhases(prev.phases, railKey);
  next.currentPhase = PHASE_ORDER.reduce<ResearchPhaseKey>((live, k) => (next.phases[k] === 'live' ? k : live), 'scoping');

  const push = (item: RunFeedItem) => { next.feed = [...next.feed, item]; };

  switch (kind) {
    case 'scope':
      push({ id: nextId(), kind: 'scope', objective: String(payload.objective || ''), mustHaves: (payload.must_haves || []).map(String), deliverable: String(payload.deliverable || '') });
      break;
    case 'research_plan':
      push({ id: nextId(), kind: 'research_plan', points: (payload.plan_points || []).map(String).slice(0, 5) });
      break;
    case 'agent_dispatch':
      push({ id: nextId(), kind: 'agent_dispatch', nodeId: String(payload.node_id || ''), question: String(payload.question || payload.message || '') });
      break;
    case 'source_added':
      push({ id: nextId(), kind: 'source_added', title: String(payload.title || payload.url || ''), url: String(payload.url || ''), sourceType: String(payload.source_type || 'web') });
      next.telemetry.sources += 1;
      break;
    case 'section_written':
      push({ id: nextId(), kind: 'section_written', title: String(payload.section_title || payload.message || '') });
      break;
    case 'tool_call': {
      const status = String(payload.status || '');
      const tool = String(payload.tool_name || 'tool');
      // Count a tool call once, when it is dispatched/routed, not on completion.
      if (status === 'tool_dispatched' || status === 'tool_routed') next.telemetry.toolCalls += 1;
      if (status === 'tool_completed' && typeof payload.source_count === 'number') {
        // Sources surfaced by search that never persist as citations still show
        // in the tool card's result count; persisted sources arrive separately.
      }
      // Collapse the lifecycle of one tool into a single feed row: update the
      // last matching running tool_call for this node/tool instead of appending.
      const idx = [...prev.feed].reverse().findIndex((f) => f.kind === 'tool_call' && f.running && f.tool === tool && f.nodeId === (payload.node_id ? String(payload.node_id) : undefined));
      const running = !(status === 'tool_completed' || status === 'tool_failed');
      const failed = status === 'tool_failed';
      if (idx >= 0 && (status === 'tool_completed' || status === 'tool_failed')) {
        const realIdx = prev.feed.length - 1 - idx;
        const existing = prev.feed[realIdx] as Extract<RunFeedItem, { kind: 'tool_call' }>;
        const updated: RunFeedItem = { ...existing, status, running, failed, sourceCount: typeof payload.source_count === 'number' ? payload.source_count : existing.sourceCount, elapsedSeconds: typeof payload.elapsed_seconds === 'number' ? payload.elapsed_seconds : existing.elapsedSeconds };
        next.feed = prev.feed.map((f, i) => (i === realIdx ? updated : f));
      } else if (status === 'tool_dispatched' || status === 'tool_routed') {
        push({ id: nextId(), kind: 'tool_call', tool, nodeId: payload.node_id ? String(payload.node_id) : undefined, status, query: toolQuery(payload), sourceCount: typeof payload.source_count === 'number' ? payload.source_count : undefined, elapsedSeconds: typeof payload.elapsed_seconds === 'number' ? payload.elapsed_seconds : undefined, running, failed });
      }
      break;
    }
    case 'phase':
    default: {
      // Thought lines: only the human-readable "started" transitions read well
      // as thoughts; skip terse status pings to keep the feed calm.
      const status = String(payload.status || '');
      const message = String(payload.message || '');
      if (message && (status === 'started' || status === 'skipped')) {
        push({ id: nextId(), kind: 'thought', text: message });
      }
      break;
    }
  }

  // Token estimate: a display heuristic, not real provider usage. Grows with the
  // volume of activity so the tile animates plausibly during a run.
  next.telemetry.tokens = 1200 + next.feed.length * 640;
  return next;
}

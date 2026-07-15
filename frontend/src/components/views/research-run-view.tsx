'use client';

import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { useAppStore } from '@/store/app-store';
import { useWorkspace } from '@/components/workspace-provider';
import {
  PhaseState,
  RESEARCH_PHASES,
  ResearchPhaseKey,
  RunFeedItem,
  RunProgress,
} from '@/lib/api';
import { emptyRunProgress } from '@/lib/research-feed';

/* ============================================================================
 * Research Run — live progress view.
 *
 * Fixed components (design: Research Run.dc.html), driven by dynamic run data:
 *   - top chrome (elapsed, depth, model, stop) + thin progress bar
 *   - query bar with a phase status kicker
 *   - left rail: Pipeline (6 phases) + Live telemetry (4 tiles)
 *   - right feed: typed items (thought, scope, agent, tool, search, source,
 *     section, report-ready) rendered from the reduced event stream.
 *
 * Every component reads only from `RunProgress`, so the same markup renders live
 * SSE data or the static `__fixtures` sample used for design review.
 * ==========================================================================*/

const MONO: React.CSSProperties = { fontFamily: 'var(--font-mono)' };

function fmtTime(sec: number): string {
  const s = Math.floor(sec);
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
}
function fmtTok(n: number): string {
  return n >= 1000 ? `${(n / 1000).toFixed(1).replace(/\.0$/, '')}k` : String(n);
}

/* ---- Left rail: pipeline ---------------------------------------------------*/
function PipelineRail({ phases }: { phases: Record<ResearchPhaseKey, PhaseState> }) {
  return (
    <div>
      <div className="sg-mono" style={{ ...MONO, fontSize: '10px', letterSpacing: '.15em', textTransform: 'uppercase', color: 'var(--text-faint)', marginBottom: '18px' }}>Pipeline</div>
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        {RESEARCH_PHASES.map((phase, i) => {
          const state = phases[phase.key];
          const pending = state === 'queued';
          const active = state === 'live';
          const done = state === 'done';
          return (
            <div key={phase.key} style={{ display: 'flex', gap: '13px', alignItems: 'stretch', padding: '12px 0 13px', opacity: pending ? 0.55 : 1, transition: 'opacity .4s ease', borderTop: i === 0 ? '1px solid transparent' : '1px solid var(--border)' }}>
              <div style={{ flexShrink: 0, width: '2px', background: active ? 'var(--accent-2)' : done ? 'var(--border-strong)' : 'var(--border)', transition: 'background .4s' }} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: '9px' }}>
                  <span className="sg-mono" style={{ ...MONO, fontSize: '15px', letterSpacing: '.02em', color: pending ? 'var(--text-faint)' : 'var(--text)' }}>{String(i + 1).padStart(2, '0')}</span>
                  <span className={`sg-mono${active ? ' rn-dot' : ''}`} style={{ ...MONO, fontSize: '9px', letterSpacing: '.18em', textTransform: 'uppercase', padding: '2px 7px', border: `1px solid ${active ? 'var(--accent-2)' : 'var(--border)'}`, color: active ? 'var(--accent-2)' : done ? 'var(--text-dim)' : 'var(--text-faint)' }}>{active ? 'live' : done ? 'done' : 'queued'}</span>
                </div>
                <div style={{ fontSize: '15px', fontWeight: 500, marginTop: '5px', color: pending ? 'var(--text-dim)' : 'var(--text)' }}>{phase.label}</div>
                <div style={{ fontSize: '12px', fontStyle: 'italic', color: 'var(--text-faint)', marginTop: '1px' }}>{phase.cap}</div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ---- Left rail: telemetry --------------------------------------------------*/
function TelemetryTile({ value, label }: { value: string; label: string }) {
  return (
    <div style={{ border: '1px solid var(--border)', background: 'var(--surface)', borderRadius: '11px', padding: '12px 13px' }}>
      <div style={{ fontSize: '24px', fontWeight: 400, letterSpacing: '-.02em' }}>{value}</div>
      <div className="sg-mono" style={{ ...MONO, fontSize: '9.5px', letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--text-faint)', marginTop: '3px' }}>{label}</div>
    </div>
  );
}
function LiveTelemetry({ progress }: { progress: RunProgress }) {
  const { telemetry } = progress;
  return (
    <div>
      <div className="sg-mono" style={{ ...MONO, fontSize: '10px', letterSpacing: '.15em', textTransform: 'uppercase', color: 'var(--text-faint)', marginBottom: '12px' }}>Live telemetry</div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
        <TelemetryTile value={String(telemetry.sources)} label="Sources" />
        <TelemetryTile value={String(telemetry.toolCalls)} label="Tool calls" />
        <TelemetryTile value={String(telemetry.sandboxes)} label="Sandboxes" />
        <TelemetryTile value={fmtTok(telemetry.tokens)} label="Tokens" />
      </div>
    </div>
  );
}

/* ---- Right feed item renderers --------------------------------------------*/
const Icon = {
  plus: <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>,
  wrench: <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="var(--accent-2)" strokeWidth="1.9"><path d="M14.7 6.3a4 4 0 0 0-5.4 5.4l-6 6 2 2 6-6a4 4 0 0 0 5.4-5.4l-2.6 2.6-2-2z" /></svg>,
  search: <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--accent-2)" strokeWidth="1.9"><circle cx="11" cy="11" r="7" /><line x1="21" y1="21" x2="16.65" y2="16.65" /></svg>,
  check: <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--ok)" strokeWidth="2.2"><polyline points="20 6 9 17 4 12" /></svg>,
};

function Spinner() {
  return <span className="rn-spin" style={{ width: '12px', height: '12px', border: '1.6px solid var(--border-strong)', borderTopColor: 'var(--accent-2)', borderRadius: '50%', display: 'inline-block' }} />;
}

function FeedItem({ item }: { item: RunFeedItem }) {
  switch (item.kind) {
    case 'phase':
      return (
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', margin: '10px 0 2px' }}>
          <span className="sg-mono" style={{ ...MONO, fontSize: '10.5px', letterSpacing: '.16em', textTransform: 'uppercase', color: 'var(--accent-2)' }}>{item.label}</span>
          <span style={{ flex: 1, height: '1px', background: 'var(--border)' }} />
        </div>
      );
    case 'thought':
      return (
        <div style={{ display: 'flex', gap: '11px', alignItems: 'flex-start' }}>
          <span className="rn-dot" style={{ flexShrink: 0, marginTop: '6px', width: '6px', height: '6px', borderRadius: '50%', background: 'var(--text-faint)' }} />
          <div style={{ fontSize: '16px', fontStyle: 'italic', lineHeight: 1.6, color: 'var(--text-dim)' }}>{item.text}</div>
        </div>
      );
    case 'scope':
      return (
        <div style={{ border: '1px solid var(--border)', background: 'var(--surface)', borderRadius: '13px', padding: '15px 17px' }}>
          <div className="sg-mono" style={{ ...MONO, fontSize: '10px', letterSpacing: '.12em', textTransform: 'uppercase', color: 'var(--text-faint)', marginBottom: '11px' }}>Scope</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {[item.objective && `Objective — ${item.objective}`, item.mustHaves.length ? `Must-haves — ${item.mustHaves.join(', ')}` : '', item.deliverable && `Deliverable — ${item.deliverable}`]
              .filter(Boolean)
              .map((line, i) => (
                <div key={i} style={{ display: 'flex', gap: '10px', fontSize: '15px', lineHeight: 1.5, color: 'var(--text)' }}>
                  <span style={{ color: 'var(--accent-2)', flexShrink: 0 }}>—</span><span>{line}</span>
                </div>
              ))}
          </div>
        </div>
      );
    case 'agent_dispatch':
      return (
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '10px', alignSelf: 'flex-start', padding: '8px 13px', border: '1px solid var(--border-strong)', background: 'var(--surface)', borderRadius: '10px' }}>
          <span style={{ width: '7px', height: '7px', flexShrink: 0, background: 'var(--accent-2)' }} />
          <span className="sg-mono" style={{ ...MONO, fontSize: '12px', color: 'var(--text)' }}>{item.nodeId || 'agent'}</span>
          <span style={{ fontSize: '14px', fontStyle: 'italic', color: 'var(--text-dim)' }}>{item.question}</span>
        </div>
      );
    case 'tool_call': {
      const isSearch = item.tool === 'web_search';
      return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', alignSelf: 'flex-start', maxWidth: '100%' }}>
          <div className="sg-mono" style={{ ...MONO, display: 'inline-flex', alignItems: 'center', gap: '9px', padding: '8px 12px', border: '1px solid var(--border-strong)', background: 'var(--surface-2)', borderRadius: '9px', fontSize: '12px', color: 'var(--text)' }}>
            {isSearch ? Icon.search : Icon.wrench}
            <span style={{ color: 'var(--accent-2)' }}>{item.tool}</span>
            {item.query && <span style={{ fontStyle: 'italic', color: 'var(--text-dim)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '360px' }}>&ldquo;{item.query}&rdquo;</span>}
            {item.running ? <Spinner /> : item.failed
              ? <span style={{ color: 'var(--warn)', fontSize: '11px' }}>failed</span>
              : <span style={{ color: 'var(--text-faint)', fontSize: '10.5px' }}>{typeof item.sourceCount === 'number' ? `${item.sourceCount} results` : 'done'}</span>}
          </div>
        </div>
      );
    }
    case 'source_added':
      return (
        <div className="sg-mono" style={{ ...MONO, display: 'inline-flex', alignItems: 'center', gap: '8px', alignSelf: 'flex-start', fontSize: '11.5px', color: 'var(--ok)' }}>
          {Icon.plus}
          Source added — {item.title}
        </div>
      );
    case 'section_written':
      return (
        <div className="sg-mono" style={{ ...MONO, display: 'inline-flex', alignItems: 'center', gap: '9px', alignSelf: 'flex-start', fontSize: '12px', color: 'var(--text-dim)' }}>
          {Icon.check}
          Wrote section <span style={{ color: 'var(--text)' }}>{item.title}</span>
        </div>
      );
    default:
      return null;
  }
}

/* ---- Report-ready card ----------------------------------------------------*/
function ReportReadyCard({ title, sources, onOpen }: { title: string; sources: number; onOpen: () => void }) {
  return (
    <div className="rn-rise" style={{ marginTop: '8px', border: '1px solid var(--border-strong)', background: 'var(--surface)', borderRadius: '18px', boxShadow: 'var(--shadow)', overflow: 'hidden' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '14px 20px', borderBottom: '1px solid var(--border)', background: 'var(--surface-2)' }}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--ok)" strokeWidth="2"><path d="M20 6 9 17l-5-5" /></svg>
        <span className="sg-mono" style={{ ...MONO, fontSize: '10.5px', letterSpacing: '.15em', textTransform: 'uppercase', color: 'var(--ok)' }}>Report ready</span>
        <span className="sg-mono" style={{ ...MONO, marginLeft: 'auto', fontSize: '11px', color: 'var(--text-faint)' }}>{sources} sources · v1</span>
      </div>
      <article style={{ padding: '26px 30px 28px' }}>
        <div className="sg-mono" style={{ ...MONO, fontSize: '10.5px', letterSpacing: '.16em', textTransform: 'uppercase', color: 'var(--accent-2)', marginBottom: '13px' }}>Research Report</div>
        <h2 style={{ margin: '0 0 20px', fontSize: '27px', fontWeight: 400, lineHeight: 1.15, letterSpacing: '-.02em' }}>{title}</h2>
        <button onClick={onOpen} style={{ display: 'inline-flex', alignItems: 'center', gap: '9px', height: '44px', padding: '0 22px', border: 'none', borderRadius: '11px', background: 'var(--accent)', color: '#fff', ...MONO, fontSize: '12.5px', fontWeight: 500, cursor: 'pointer' }}>
          Open full report
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2"><line x1="5" y1="12" x2="19" y2="12" /><polyline points="12 5 19 12 12 19" /></svg>
        </button>
      </article>
    </div>
  );
}

/* ---- Main view ------------------------------------------------------------*/
export function ResearchRunView({ __fixtures }: { __fixtures?: RunProgress }) {
  const { activeRunId, setView, setActiveReportId } = useAppStore();
  const { runs, runProgress, cancelResearch } = useWorkspace();
  const feedRef = useRef<HTMLDivElement>(null);
  const [elapsed, setElapsed] = useState(0);

  const run = runs.find((item) => item.id === activeRunId);
  const progress = __fixtures ?? (activeRunId ? runProgress[activeRunId] : undefined) ?? emptyRunProgress();
  const running = !!run && !['completed', 'failed', 'cancelled'].includes(run.status);
  const finished = !!run && run.status === 'completed';

  // Live tick while running; the effect owns the impure clock reads so render
  // stays pure. `elapsed` state is only used during an active run.
  const startedAtMs = run?.started_at ? new Date(run.started_at).getTime() : null;
  useEffect(() => {
    if (!running) return;
    const anchor = startedAtMs ?? Date.now();
    const tick = setInterval(() => setElapsed((Date.now() - anchor) / 1000), 250);
    return () => clearInterval(tick);
  }, [running, startedAtMs]);

  // A finished run shows its fixed wall-clock duration, derived during render.
  const finalElapsed = finished && run?.finished_at && run.started_at
    ? (new Date(run.finished_at).getTime() - new Date(run.started_at).getTime()) / 1000
    : null;
  const shownElapsed = finalElapsed ?? elapsed;

  // Follow the feed as new items land.
  const feedLen = progress.feed.length;
  useLayoutEffect(() => {
    const el = feedRef.current;
    if (el && el.scrollHeight - el.scrollTop - el.clientHeight < 400) el.scrollTop = el.scrollHeight;
  }, [feedLen, running]);

  const phaseLabel = useMemo(() => RESEARCH_PHASES.find((p) => p.key === progress.currentPhase)?.label ?? 'Scoping', [progress.currentPhase]);
  const kicker = finished ? 'REPORT READY' : phaseLabel.toUpperCase();
  const strength = String(run?.run_data?.strength ?? '');
  const depthLabel = strength === '3' ? 'Ultra' : strength === '2' ? 'Deep' : strength === '1' ? 'Quick' : 'Research';
  const modelLabel = String(run?.run_data?.model_id ?? 'Model');

  const totalPhases = RESEARCH_PHASES.length;
  const donePhases = RESEARCH_PHASES.filter((p) => progress.phases[p.key] === 'done').length;
  const progressPct = finished ? 100 : Math.round((donePhases / totalPhases) * 100);

  const openReport = () => {
    if (run?.report_id) { setActiveReportId(run.report_id); setView('report'); }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0, width: '100%', overflow: 'hidden', background: 'var(--bg)' }}>
      {/* top chrome */}
      <header style={{ flexShrink: 0, display: 'flex', alignItems: 'center', gap: '14px', height: '58px', padding: '0 20px', background: 'var(--surface)', borderBottom: '1px solid var(--border)' }}>
        <span className="sg-mono" style={{ ...MONO, display: 'flex', alignItems: 'center', gap: '7px', fontSize: '11px', letterSpacing: '.04em', color: 'var(--text-faint)' }}>
          {Icon.search} Deep research run
        </span>
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '9px' }}>
          <span className="sg-mono" style={{ ...MONO, display: 'flex', alignItems: 'center', gap: '7px', height: '32px', padding: '0 12px', border: '1px solid var(--border)', background: 'var(--surface-2)', borderRadius: '9px', fontSize: '12px', color: 'var(--text)' }}>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="var(--text-dim)" strokeWidth="1.9"><circle cx="12" cy="12" r="9" /><polyline points="12 7 12 12 15 14" /></svg>
            {fmtTime(shownElapsed)}
          </span>
          <span className="sg-mono" style={{ ...MONO, display: 'flex', alignItems: 'center', gap: '7px', height: '32px', padding: '0 12px', border: '1px solid var(--border)', background: 'var(--surface-2)', borderRadius: '9px', fontSize: '12px', color: 'var(--text)' }}><span style={{ width: '7px', height: '7px', background: 'var(--text-dim)' }} />{depthLabel}</span>
          <span className="sg-mono" style={{ ...MONO, display: 'flex', alignItems: 'center', gap: '7px', height: '32px', padding: '0 12px', border: '1px solid var(--border)', background: 'var(--surface-2)', borderRadius: '9px', fontSize: '12px', color: 'var(--text)', maxWidth: '220px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{modelLabel}</span>
          {running && run && (
            <button onClick={() => void cancelResearch(run.id).catch(() => undefined)} style={{ display: 'flex', alignItems: 'center', gap: '7px', height: '32px', padding: '0 14px', border: '1px solid var(--border-strong)', background: 'var(--surface-2)', color: 'var(--text)', borderRadius: '9px', cursor: 'pointer', ...MONO, fontSize: '12px', fontWeight: 500 }}>
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="6" y="6" width="12" height="12" rx="1.5" /></svg>Stop
            </button>
          )}
        </div>
      </header>
      <div style={{ flexShrink: 0, height: '2px', background: 'var(--border)' }}><div style={{ height: '100%', background: 'var(--accent)', width: `${progressPct}%`, transition: 'width .35s ease' }} /></div>

      {/* query bar */}
      <div style={{ flexShrink: 0, padding: '22px 28px 20px', borderBottom: '1px solid var(--border)', background: 'var(--bg)' }}>
        <div style={{ maxWidth: '1180px', margin: '0 auto' }}>
          <div className="sg-mono" style={{ ...MONO, display: 'flex', alignItems: 'center', gap: '9px', fontSize: '10.5px', letterSpacing: '.16em', textTransform: 'uppercase', color: 'var(--accent-2)', marginBottom: '10px' }}>
            <span className={running ? 'rn-dot' : ''} style={{ width: '7px', height: '7px', borderRadius: '50%', background: running ? 'var(--accent)' : 'var(--ok)' }} />
            {kicker}
          </div>
          <h1 style={{ margin: 0, fontSize: 'clamp(21px,2.6vw,28px)', fontWeight: 400, lineHeight: 1.25, letterSpacing: '-.02em', maxWidth: '40ch' }}>{run?.query || 'Research run'}</h1>
          <div className="sg-mono" style={{ ...MONO, marginTop: '10px', fontSize: '11.5px', color: 'var(--text-dim)' }}>
            {finished ? `Completed in ${fmtTime(shownElapsed)}` : running ? `Running · ${fmtTime(shownElapsed)} elapsed` : run?.status === 'failed' ? 'Run failed' : 'Queued'} · {depthLabel} depth
          </div>
        </div>
      </div>

      {/* body */}
      <div style={{ flex: 1, minHeight: 0, display: 'flex', background: 'var(--bg)' }}>
        <div style={{ width: '100%', maxWidth: '1180px', margin: '0 auto', display: 'grid', gridTemplateColumns: '296px 1fr', minHeight: 0 }}>
          <aside style={{ borderRight: '1px solid var(--border)', padding: '26px 22px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '26px' }}>
            <PipelineRail phases={progress.phases} />
            <LiveTelemetry progress={progress} />
            <div style={{ marginTop: 'auto', paddingTop: '8px' }}>
              <div className="sg-mono" style={{ ...MONO, display: 'flex', alignItems: 'center', gap: '8px', fontSize: '10.5px', color: 'var(--text-faint)' }}>
                <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--warn)', flexShrink: 0 }} />
                QA agent re-checks every claim before the report is written.
              </div>
            </div>
          </aside>

          <div ref={feedRef} style={{ minHeight: 0, overflowY: 'auto', overscrollBehavior: 'contain', padding: '26px clamp(20px,4vw,44px) 120px' }}>
            <div style={{ maxWidth: '760px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '14px' }}>
              {progress.feed.map((item) => (
                <div key={item.id} className="rn-in" style={{ display: 'flex', flexDirection: 'column' }}>
                  <FeedItem item={item} />
                </div>
              ))}

              {finished && run && (
                <ReportReadyCard title={run.query} sources={progress.telemetry.sources} onOpen={openReport} />
              )}

              {run?.status === 'failed' && (
                <div style={{ color: 'var(--color-danger)', fontStyle: 'italic' }}>{progress.activity.error || run.error_message || 'Research failed.'}</div>
              )}

              {running && (
                <div style={{ display: 'inline-flex', alignItems: 'center', gap: '9px', alignSelf: 'flex-start', padding: '4px 2px' }}>
                  {[0, 1, 2].map((i) => (
                    <span key={i} className="rn-dot" style={{ width: '7px', height: '7px', borderRadius: '50%', background: 'var(--accent-2)', animationDelay: `${i * 0.18}s` }} />
                  ))}
                </div>
              )}

              {!progress.feed.length && !running && !finished && (
                <p style={{ color: 'var(--text-faint)', fontSize: '14px' }}>Waiting for the research run to start…</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

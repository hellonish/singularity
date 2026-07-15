'use client';

import { useEffect, useState } from 'react';
import { ClarificationQuestion, ResearchBrief } from '@/lib/api';
import { useAppStore } from '@/store/app-store';
import { useWorkspace } from '@/components/workspace-provider';

type PreparationStage = 'request_breakdown' | 'entity_resolution' | 'finalizing_plan';
type StepState = 'done' | 'live' | 'queued';

const STAGE_INDEX: Record<PreparationStage, number> = {
  request_breakdown: 1,
  entity_resolution: 2,
  finalizing_plan: 3,
};

function preparationStage(value: unknown): PreparationStage {
  return value === 'entity_resolution' || value === 'finalizing_plan'
    ? value
    : 'request_breakdown';
}

export function ResearchPreparationView() {
  const { activePreparationId, setActivePreparationId, setActiveRunId, setActiveReportId, setView } = useAppStore();
  const { preparations, preparationActivity, loadResearchPreparation, answerResearchPreparation, startPreparedResearch, cancelResearchPreparation } = useWorkspace();
  const preparation = activePreparationId ? preparations[activePreparationId] : undefined;
  const [answer, setAnswer] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!activePreparationId || preparation) return;
    void loadResearchPreparation(activePreparationId).catch(() => {
      setActivePreparationId(null);
      setView('grid');
    });
  }, [activePreparationId, loadResearchPreparation, preparation, setActivePreparationId, setView]);

  useEffect(() => {
    if (!activePreparationId || preparation?.status !== 'draft') return;
    const timer = window.setInterval(() => {
      void loadResearchPreparation(activePreparationId).catch(() => undefined);
    }, 1_000);
    return () => window.clearInterval(timer);
  }, [activePreparationId, loadResearchPreparation, preparation?.status]);

  const cancelDraft = async () => {
    if (activePreparationId) await cancelResearchPreparation(activePreparationId).catch(() => undefined);
    setActivePreparationId(null);
    setView('grid');
  };

  const brief = (preparation?.status === 'ready' ? preparation.final_brief : preparation?.plan_data) as Partial<ResearchBrief> | undefined;
  const questions = (preparation?.plan_data.questions ?? []) as ClarificationQuestion[];
  const current = preparation ? questions[preparation.current_question_index] : undefined;
  const total = questions.length;

  if (!preparation || preparation.status === 'draft' || preparation.status === 'failed') {
    const failed = preparation?.status === 'failed' || preparationActivity?.status === 'failed';
    const auto = (preparation?.approval_mode ?? preparationActivity?.approvalMode) === 'auto';
    const stage = preparationStage(preparation?.plan_data.preparation_stage);
    const liveIndex = STAGE_INDEX[stage];
    const heading = stage === 'entity_resolution'
      ? 'Resolving the target entity'
      : stage === 'finalizing_plan'
        ? 'Preparing your approval plan'
        : 'Breaking down your request';
    const steps: Array<{ label: string; state: StepState }> = [
      { label: 'Request received', state: 'done' },
      { label: 'Breaking down the request', state: liveIndex > 1 ? 'done' : liveIndex === 1 ? 'live' : 'queued' },
      { label: auto ? 'Resolving entity ambiguity automatically' : 'Checking whether clarification is needed', state: liveIndex > 2 ? 'done' : liveIndex === 2 ? 'live' : 'queued' },
      { label: 'Drafting the research plan for your approval', state: liveIndex === 3 ? 'live' : 'queued' },
    ];
    return (
      <main style={{ flex: 1, minHeight: 0, overflowY: 'auto', background: 'var(--bg)', padding: '56px 28px' }}>
        <section style={{ width: '100%', maxWidth: '820px', margin: '0 auto' }}>
          <div className="sg-mono" style={{ fontSize: '10.5px', letterSpacing: '.15em', textTransform: 'uppercase', color: failed ? 'var(--warn)' : 'var(--accent-2)' }}>
            {failed ? 'Preparation stopped' : 'Research process · Preparing plan'}
          </div>
          <h1 style={{ margin: '12px 0 8px', fontSize: '30px', fontWeight: 400, lineHeight: 1.2 }}>
            {failed ? 'The research plan could not be prepared' : heading}
          </h1>
          <p style={{ margin: 0, color: 'var(--text-dim)', lineHeight: 1.55 }}>
            {preparation?.query ?? preparationActivity?.query ?? 'Loading the research plan…'}
          </p>

          <div aria-live="polite" style={{ marginTop: '28px', padding: '22px 24px', border: '1px solid var(--border-strong)', borderRadius: '16px', background: 'var(--surface)' }}>
            {failed ? (
              <p style={{ margin: 0, color: 'var(--text-dim)', lineHeight: 1.55 }}>
                {preparation?.error_message ?? preparationActivity?.message ?? 'Research preparation could not be completed.'}
              </p>
            ) : (
              <div style={{ display: 'grid', gap: '16px' }}>
                {steps.map(({ label, state }) => (
                  <div key={label} style={{ display: 'flex', alignItems: 'center', gap: '12px', color: state === 'done' ? 'var(--text)' : 'var(--text-dim)' }}>
                    {state === 'done'
                      ? <span aria-hidden="true" style={{ color: 'var(--ok)', fontSize: '17px' }}>✓</span>
                      : state === 'live'
                        ? <span aria-hidden="true" className="rn-spin" style={{ width: '12px', height: '12px', border: '1.6px solid var(--border-strong)', borderTopColor: 'var(--accent-2)', borderRadius: '50%', display: 'inline-block' }} />
                        : <span aria-hidden="true" style={{ width: '12px', height: '12px', border: '1.6px solid var(--border-strong)', borderRadius: '50%', display: 'inline-block', opacity: .65 }} />}
                    <span>{label}</span>
                  </div>
                ))}
                <p className="sg-mono" style={{ margin: '4px 0 0', fontSize: '10.5px', color: 'var(--text-faint)' }}>
                  Research will not start until you approve the plan.
                </p>
              </div>
            )}
          </div>

          {failed ? (
            <button type="button" onClick={() => { setActivePreparationId(null); setView('grid'); }} style={{ marginTop: '18px', border: 0, background: 'transparent', color: 'var(--text-dim)', cursor: 'pointer' }}>
              Back to new research
            </button>
          ) : (
            <button type="button" onClick={() => void cancelDraft()} style={{ marginTop: '18px', border: 0, background: 'transparent', color: 'var(--text-dim)', cursor: 'pointer' }}>
              Cancel research
            </button>
          )}
        </section>
      </main>
    );
  }

  const leave = async () => {
    if (!['started', 'cancelled'].includes(preparation.status)) await cancelResearchPreparation(preparation.id).catch(() => undefined);
    setActivePreparationId(null);
    setView('grid');
  };

  const submitAnswer = async () => {
    if (!current || !answer.trim() || busy) return;
    setBusy(true);
    try {
      await answerResearchPreparation(preparation.id, current.question_id, answer.trim());
      setAnswer('');
    }
    finally { setBusy(false); }
  };

  const start = async () => {
    setBusy(true);
    try {
      const run = await startPreparedResearch(preparation.id);
      setActiveRunId(run.id);
      if (run.report_id) setActiveReportId(run.report_id);
      setView('run');
    } finally { setBusy(false); }
  };

  return (
    <main style={{ flex: 1, minHeight: 0, overflowY: 'auto', background: 'var(--bg)', padding: '56px 28px' }}>
      <section style={{ width: '100%', maxWidth: '820px', margin: '0 auto' }}>
        <div className="sg-mono" style={{ fontSize: '10.5px', letterSpacing: '.15em', textTransform: 'uppercase', color: 'var(--accent-2)' }}>
          Research plan · {preparation.approval_mode === 'auto' ? 'Auto resolve' : 'Ask mode'} · Approval required
        </div>
        <h1 style={{ margin: '12px 0 8px', fontSize: '30px', fontWeight: 400, lineHeight: 1.2 }}>Review the approach before research starts</h1>
        <p style={{ margin: 0, color: 'var(--text-dim)', lineHeight: 1.55 }}>{preparation.query}</p>

        <div style={{ marginTop: '28px', padding: '22px 24px', border: '1px solid var(--border-strong)', borderRadius: '16px', background: 'var(--surface)' }}>
          <div className="sg-mono" style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '.12em', color: 'var(--text-faint)' }}>{preparation.status === 'ready' ? 'Final plan' : 'Proposed plan'}</div>
          <ol style={{ margin: '16px 0 0', paddingLeft: '22px', display: 'grid', gap: '11px', lineHeight: 1.5 }}>
            {(brief?.plan_points ?? []).slice(0, 5).map((point) => <li key={point}>{point}</li>)}
          </ol>
        </div>

        {(brief?.execution_requirements?.length ?? 0) > 0 && (
          <div style={{ marginTop: '18px', padding: '22px 24px', border: '1px solid var(--border-strong)', borderRadius: '16px', background: 'var(--surface)' }}>
            <div className="sg-mono" style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '.12em', color: 'var(--text-faint)' }}>Isolated execution requiring approval</div>
            <p style={{ margin: '10px 0 14px', color: 'var(--text-dim)', lineHeight: 1.5 }}>
              Starting this plan authorizes the following task-scoped Sandbox work. No provider or production credentials are sent to it.
            </p>
            <div style={{ display: 'grid', gap: '10px' }}>
              {brief?.execution_requirements?.map((requirement) => (
                <div key={`${requirement.kind}:${requirement.resource_reference ?? requirement.profile}`} style={{ padding: '12px 14px', border: '1px solid var(--border)', borderRadius: '10px', background: 'var(--surface-2)' }}>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', alignItems: 'baseline' }}>
                    <strong style={{ fontSize: '13.5px', fontWeight: 600, textTransform: 'capitalize' }}>{requirement.kind}</strong>
                    <span className="sg-mono" style={{ fontSize: '10.5px', color: 'var(--accent-2)' }}>{requirement.profile}</span>
                    {requirement.required && <span className="sg-mono" style={{ fontSize: '10px', color: 'var(--warn)' }}>required</span>}
                  </div>
                  {requirement.resource_reference && (
                    <div className="sg-mono" style={{ marginTop: '7px', overflowWrap: 'anywhere', fontSize: '10.5px', color: 'var(--text-dim)' }}>{requirement.resource_reference}</div>
                  )}
                  {requirement.actions.length > 0 && (
                    <div style={{ marginTop: '7px', fontSize: '12px', color: 'var(--text-faint)' }}>{requirement.actions.join(' · ')}</div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {preparation.status === 'awaiting_input' && current && (
          <div style={{ marginTop: '18px', padding: '24px', border: '1px solid var(--border-strong)', borderRadius: '16px', background: 'var(--surface)' }}>
            <div className="sg-mono" style={{ fontSize: '10.5px', color: 'var(--text-faint)' }}>Question {preparation.current_question_index + 1} of {total}</div>
            <h2 style={{ margin: '10px 0 6px', fontSize: '21px', fontWeight: 500, lineHeight: 1.35 }}>{current.text}</h2>
            {current.reason && <p style={{ margin: '0 0 16px', fontSize: '13px', color: 'var(--text-dim)' }}>{current.reason}</p>}
            <textarea autoFocus value={answer} onChange={(event) => setAnswer(event.target.value)} rows={4} placeholder="Your answer" style={{ width: '100%', boxSizing: 'border-box', resize: 'vertical', padding: '13px', border: '1px solid var(--border-strong)', borderRadius: '11px', background: 'var(--surface-2)', color: 'var(--text)', font: 'inherit', outline: 'none' }} />
            <button type="button" disabled={!answer.trim() || busy} onClick={() => void submitAnswer()} style={{ marginTop: '13px', height: '40px', padding: '0 18px', border: 0, borderRadius: '10px', background: 'var(--accent)', color: '#fff', cursor: answer.trim() && !busy ? 'pointer' : 'default', opacity: answer.trim() && !busy ? 1 : .55 }}>Save and continue</button>
          </div>
        )}

        {preparation.status === 'ready' && (
          <div style={{ marginTop: '18px', padding: '22px 24px', border: '1px solid var(--border-strong)', borderRadius: '16px', background: 'var(--surface)' }}>
            <h2 style={{ margin: 0, fontSize: '20px', fontWeight: 500 }}>Ready to research</h2>
            <p style={{ margin: '8px 0 18px', color: 'var(--text-dim)', lineHeight: 1.5 }}>{brief?.refined_objective}</p>
            {(brief?.assumptions?.length ?? 0) > 0 && <p style={{ fontSize: '13px', color: 'var(--text-dim)' }}>Assumptions: {brief?.assumptions?.join('; ')}</p>}
            <button type="button" disabled={busy} onClick={() => void start()} style={{ height: '42px', padding: '0 20px', border: 0, borderRadius: '10px', background: 'var(--accent)', color: '#fff', cursor: busy ? 'default' : 'pointer' }}>{busy ? 'Starting research…' : 'Approve plan and start research'}</button>
          </div>
        )}

        <button type="button" onClick={() => void leave()} style={{ marginTop: '18px', border: 0, background: 'transparent', color: 'var(--text-dim)', cursor: 'pointer' }}>Cancel and go back</button>
      </section>
    </main>
  );
}

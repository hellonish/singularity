'use client';

import { useEffect, useState } from 'react';
import { ClarificationQuestion, ResearchBrief } from '@/lib/api';
import { useAppStore } from '@/store/app-store';
import { useWorkspace } from '@/components/workspace-provider';

export function ResearchPreparationView() {
  const { activePreparationId, setActivePreparationId, setActiveRunId, setActiveReportId, setView } = useAppStore();
  const { preparations, loadResearchPreparation, answerResearchPreparation, startPreparedResearch, cancelResearchPreparation } = useWorkspace();
  const preparation = activePreparationId ? preparations[activePreparationId] : undefined;
  const [answer, setAnswer] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (activePreparationId && !preparation) void loadResearchPreparation(activePreparationId).catch(() => setView('grid'));
  }, [activePreparationId, loadResearchPreparation, preparation, setView]);

  const brief = (preparation?.status === 'ready' ? preparation.final_brief : preparation?.plan_data) as Partial<ResearchBrief> | undefined;
  const questions = (preparation?.plan_data.questions ?? []) as ClarificationQuestion[];
  const current = preparation ? questions[preparation.current_question_index] : undefined;
  const total = questions.length;

  if (!preparation) {
    return <div style={{ flex: 1, padding: '80px 32px', color: 'var(--text-dim)' }}>Loading the research plan…</div>;
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
          Research plan · Ask for approval
        </div>
        <h1 style={{ margin: '12px 0 8px', fontSize: '30px', fontWeight: 400, lineHeight: 1.2 }}>Review the approach before research starts</h1>
        <p style={{ margin: 0, color: 'var(--text-dim)', lineHeight: 1.55 }}>{preparation.query}</p>

        <div style={{ marginTop: '28px', padding: '22px 24px', border: '1px solid var(--border-strong)', borderRadius: '16px', background: 'var(--surface)' }}>
          <div className="sg-mono" style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '.12em', color: 'var(--text-faint)' }}>{preparation.status === 'ready' ? 'Final plan' : 'Proposed plan'}</div>
          <ol style={{ margin: '16px 0 0', paddingLeft: '22px', display: 'grid', gap: '11px', lineHeight: 1.5 }}>
            {(brief?.plan_points ?? []).slice(0, 5).map((point) => <li key={point}>{point}</li>)}
          </ol>
        </div>

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
            <button type="button" disabled={busy} onClick={() => void start()} style={{ height: '42px', padding: '0 20px', border: 0, borderRadius: '10px', background: 'var(--accent)', color: '#fff', cursor: busy ? 'default' : 'pointer' }}>Start research</button>
          </div>
        )}

        <button type="button" onClick={() => void leave()} style={{ marginTop: '18px', border: 0, background: 'transparent', color: 'var(--text-dim)', cursor: 'pointer' }}>Cancel and go back</button>
      </section>
    </main>
  );
}

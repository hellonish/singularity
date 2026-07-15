'use client';

import { useState, useEffect } from 'react';
import { useAppStore } from '@/store/app-store';
import { useWorkspace } from '@/components/workspace-provider';
import { useAuthSession } from '@/components/auth/auth-guard';
import { Composer } from '../ui/composer';

function relativeTime(value: string): string {
  if (!value.endsWith('Z')) {
    value += 'Z';
  }
  const date = new Date(value);
  const minutes = Math.max(0, Math.round((Date.now() - date.getTime()) / 60_000));
  if (minutes < 1) return date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
  if (minutes < 60) return `${minutes}m ago`;
  if (minutes < 1_440) return `${Math.round(minutes / 60)}h ago`;
  return `${Math.round(minutes / 1_440)}d ago`;
}

export function GridView() {
  const { reports, runs, loading } = useWorkspace();
  const { setView, setActiveReportId, setActiveRunId, setActivePreparationId } = useAppStore();
  const { user } = useAuthSession();

  const [greetingMessage, setGreetingMessage] = useState<{ prefix: string; suffix: string } | null>(null);
  const firstName = user?.display_name?.split(' ')[0] || 'there';

  useEffect(() => {
    const hour = new Date().getHours();

    const morning = [
      { prefix: `Hello ${firstName}, `, suffix: "Ready for today's adventure?" },
      { prefix: `Hello ${firstName}, `, suffix: "Let's make today a great one!" },
      { prefix: `Hello ${firstName}, `, suffix: "Rise and shine!" },
      { prefix: `Hello ${firstName}, `, suffix: "Time to build something amazing!" }
    ];

    const afternoon = [
      { prefix: `Hello ${firstName}, `, suffix: "How is your day going?" },
      { prefix: `Hello ${firstName}, `, suffix: "Keep up the great momentum!" },
      { prefix: `Hello ${firstName}, `, suffix: "Hope you're having a productive afternoon!" },
      { prefix: `Hello ${firstName}, `, suffix: "Almost there, keep it up!" }
    ];

    const evening = [
      { prefix: `Hello ${firstName}, `, suffix: "Your hardwork will pay off!" },
      { prefix: `Hello ${firstName}, `, suffix: "Winding down or gearing up?" },
      { prefix: `Hello ${firstName}, `, suffix: "Evening is the time for big ideas." },
      { prefix: `Hello ${firstName}, `, suffix: "Hope you had a great day!" }
    ];

    const night = [
      { prefix: `Hey ${firstName}, `, suffix: "Looks like you're a night owl like me!" },
      { prefix: `Hello ${firstName}, `, suffix: "Burning the midnight oil?" },
      { prefix: `Hello ${firstName}, `, suffix: "Quiet hours, perfect for focus." },
      { prefix: `Hello ${firstName}, `, suffix: "Remember to get some rest soon!" }
    ];

    let messages: { prefix: string; suffix: string }[];
    if (hour >= 5 && hour < 12) {
      messages = morning;
    } else if (hour >= 12 && hour < 17) {
      messages = afternoon;
    } else if (hour >= 17 && hour < 22) {
      messages = evening;
    } else {
      messages = night;
    }

    const frame = window.requestAnimationFrame(() => {
      setGreetingMessage(messages[Math.floor(Math.random() * messages.length)]);
    });
    return () => window.cancelAnimationFrame(frame);
  }, [firstName]);

  const handleOpenProject = (reportId: string, runId?: string) => {
    const run = runId ? runs.find((item) => item.id === runId) : undefined;
    setActiveReportId(reportId);
    if (run && ['queued', 'running'].includes(run.status)) {
      setActivePreparationId(null);
      setActiveRunId(run.id);
      setView('run');
      return;
    }
    setActiveRunId(null);
    setView('report');
  };

  return (
    <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
      <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', overscrollBehavior: 'contain' }}>
        <div style={{ maxWidth: '1180px', margin: '0 auto', padding: '90px 32px 40px' }}>
          <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: '16px', marginBottom: '24px' }}>
            <div>
              <h1 style={{ margin: 0, fontSize: '34px', fontWeight: 400, letterSpacing: '-.02em', lineHeight: 1.05, minHeight: '36px' }}>
                {greetingMessage ? (
                  <>{greetingMessage.prefix}<span style={{ color: 'var(--accent)' }}>{greetingMessage.suffix}</span></>
                ) : '\u00A0'}
              </h1>
            </div>
            <span className="sg-mono" style={{ fontSize: '12px', color: 'var(--text-dim)', paddingBottom: '4px' }}>{reports.length} reports</span>
          </div>
          {loading ? <p style={{ color: 'var(--text-dim)' }}>Loading your workspace…</p> : reports.length === 0 ? null : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(268px, 1fr))', gap: '16px' }}>
              {reports.map((report) => {
                const run = runs.find((item) => item.report_id === report.id);
                return <button key={report.id} onClick={() => handleOpenProject(report.id, run?.id)} className="animate-sg-rise" style={{ position: 'relative', minWidth: 0, overflow: 'hidden', cursor: 'pointer', textAlign: 'left', backgroundColor: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '14px', padding: '18px 18px 15px', boxShadow: 'var(--shadow-sm)', color: 'var(--text)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                    <span className="sg-mono" style={{ marginLeft: 'auto', fontSize: '10px', padding: '2px 7px', borderRadius: '5px', backgroundColor: report.status === 'ready' ? 'var(--accent-soft)' : 'var(--surface-3)', color: 'var(--accent-2)' }}>{run?.status ?? report.status}</span>
                  </div>
                  <h3 style={{ margin: '0 0 12px', fontSize: '17px', fontWeight: 500, lineHeight: 1.3, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden', overflowWrap: 'anywhere' }}>{report.title || 'Untitled research'}</h3>
                  <div className="sg-mono" style={{ display: 'flex', gap: '12px', fontSize: '11px', color: 'var(--text-dim)', minWidth: 0 }}><span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{relativeTime(report.updated_at)}</span><span style={{ marginLeft: 'auto', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{report.source || 'research'}</span></div>
                </button>;
              })}
            </div>
          )}
        </div>
      </div>
      <Composer />
    </div>
  );
}

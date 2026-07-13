'use client';

import { useAppStore } from '@/store/app-store';
import { REPORTS } from '@/lib/dummy-data';
import { Composer } from '../ui/composer';

export function GridView() {
  const { setView, setActiveReportId, setActiveChatId } = useAppStore();

  const handleOpenReport = (id: string, chatId?: string) => {
    const report = REPORTS.find((r) => r.id === id);
    if (!report) return;
    const cid = chatId || (report.chats[0]?.id);
    setActiveReportId(id);
    setActiveChatId(cid);
    setView('report');
  };

  return (
    <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
      <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', overscrollBehavior: 'contain' }}>
        <div style={{ maxWidth: '1180px', margin: '0 auto', padding: '90px 32px 40px' }}>
          <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: '16px', marginBottom: '24px' }}>
            <div>
              <div className="sg-mono" style={{ fontSize: '10.5px', letterSpacing: '.16em', textTransform: 'uppercase', color: 'var(--text-faint)', marginBottom: '8px' }}>Workspace</div>
              <h1 style={{ margin: 0, fontSize: '34px', fontWeight: 300, fontStyle: 'italic', letterSpacing: '-.02em', lineHeight: 1.05 }}>Recent research</h1>
            </div>
            <span className="sg-mono" style={{ fontSize: '12px', color: 'var(--text-dim)', paddingBottom: '4px' }}>{REPORTS.length} reports</span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(268px, 1fr))', gap: '16px' }}>
            {REPORTS.map((r) => (
              <div
                key={r.id}
                onClick={() => handleOpenReport(r.id)}
                className="animate-sg-rise"
                style={{ position: 'relative', cursor: 'pointer', backgroundColor: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '14px', padding: '18px 18px 15px', boxShadow: 'var(--shadow-sm)' }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                  <span className="sg-mono" style={{ marginLeft: 'auto', fontSize: '10px', padding: '2px 7px', borderRadius: '5px', backgroundColor: 'var(--accent-soft)', color: 'var(--accent-2)' }}>v{r.ver}</span>
                </div>
                <h3 style={{ margin: '0 0 12px', fontSize: '17px', fontWeight: 300, fontStyle: 'italic', lineHeight: 1.3, color: 'var(--text)' }}>{r.title}</h3>
                <div className="sg-mono" style={{ display: 'flex', gap: '12px', fontSize: '11px', color: 'var(--text-dim)' }}>
                  <span>{r.time}</span>
                  <span style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /></svg>
                    {r.chats.length}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
      <Composer />
    </div>
  );
}

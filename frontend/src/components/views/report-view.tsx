'use client';

import { useState } from 'react';
import { useAppStore } from '@/store/app-store';
import { REPORTS, BLOCKS, MODELS } from '@/lib/dummy-data';

export function ReportView() {
  const { activeReportId, activeChatId, setActiveChatId, modelId, setModelId } = useAppStore();
  
  const [chatCollapsed, setChatCollapsed] = useState(false);
  const [threadMenuOpen, setThreadMenuOpen] = useState(false);
  const [rModelMenuOpen, setRModelMenuOpen] = useState(false);
  const [reportQuery, setReportQuery] = useState('');

  const report = REPORTS.find(r => r.id === activeReportId);
  const activeChat = report?.chats.find(c => c.id === activeChatId) || report?.chats[0];

  const toggleChatCollapsed = () => setChatCollapsed(!chatCollapsed);
  const toggleThreadMenu = () => setThreadMenuOpen(!threadMenuOpen);
  const toggleRModelMenu = () => setRModelMenuOpen(!rModelMenuOpen);

  const handleReportSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!reportQuery.trim()) return;
    console.log('Sending report chat message:', reportQuery);
    setReportQuery('');
  };

  const handleReportKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleReportSend(e as unknown as React.FormEvent);
    }
  };

  const closeMenus = () => {
    setThreadMenuOpen(false);
    setRModelMenuOpen(false);
  };

  if (!report) return null;

  const chatPositionLabel = activeChat ? `${report.chats.indexOf(activeChat) + 1} of ${report.chats.length}` : '';
  const selectedModel = MODELS.flatMap(g => g.items).find(m => m.id === modelId);
  const modelName = selectedModel?.name || 'Select model';
  const modelGroup = MODELS.find(g => g.items.some(m => m.id === modelId));
  const modelDot = modelGroup?.dot || 'var(--text-faint)';

  const chatMessages = [
    { who: 'You', text: 'What is the main bottleneck for solid-state batteries?', isUser: true },
    { who: 'Singularity', text: 'The primary bottleneck is the supply of sulfide solid electrolytes and the manufacturing capacity required to process them at scale in dry-room environments.', isUser: false },
  ];

  return (
    <div style={{ flex: 1, minHeight: 0, display: 'flex', overflow: 'hidden' }}>
      
      {/* Report Body */}
      <div data-screen-label="Report" style={{ flex: 1, minWidth: 0, overflowY: 'auto' }}>
        <article style={{ maxWidth: '720px', margin: '0 auto', padding: '88px 40px 80px' }}>
          <div style={{ borderBottom: '1px solid var(--border-strong)', paddingBottom: '26px', marginBottom: '34px' }}>
            <div className="sg-mono" style={{ fontSize: '10.5px', letterSpacing: '.16em', textTransform: 'uppercase', color: 'var(--accent-2)', marginBottom: '14px' }}>Research Report</div>
            <h1 style={{ margin: '0 0 18px', fontSize: '38px', fontWeight: 300, lineHeight: 1.12, letterSpacing: '-.02em' }}>{report.title}</h1>
            <div className="sg-mono" style={{ display: 'flex', flexWrap: 'wrap', gap: '14px', fontSize: '11px', color: 'var(--text-dim)' }}>
              <span>Depth: {report.tier}</span><span>·</span><span>{report.chars}</span><span>·</span><span>v{report.ver}</span><span>·</span><span>{report.time}</span>
            </div>
          </div>

          {BLOCKS.map((b, i) => {
            if (b.type === 'lead') return <p key={i} style={{ fontSize: '21px', fontWeight: 300, lineHeight: 1.6, color: 'var(--text)', margin: '0 0 26px' }}>{b.text}</p>;
            if (b.type === 'h2') return <h2 key={i} style={{ fontSize: '15px', fontWeight: 500, letterSpacing: '.02em', color: 'var(--text)', margin: '38px 0 14px', paddingBottom: '8px', borderBottom: '1px solid var(--border)' }}>{b.text}</h2>;
            if (b.type === 'p') return <p key={i} style={{ fontSize: '17px', lineHeight: 1.72, color: 'var(--text)', margin: '0 0 18px' }}>{b.text}</p>;
            if (b.type === 'callout') return (
              <div key={i} style={{ display: 'flex', gap: '14px', margin: '24px 0', padding: '18px 20px', backgroundColor: 'var(--accent-soft)', border: '1px solid var(--border)', borderLeft: '3px solid var(--accent)', borderRadius: '12px' }}>
                <div>
                  <div className="sg-mono" style={{ fontSize: '10px', letterSpacing: '.12em', textTransform: 'uppercase', color: 'var(--accent-2)', marginBottom: '7px' }}>{b.label}</div>
                  <div style={{ fontSize: '17px', lineHeight: 1.6, fontStyle: 'italic' }}>{b.text}</div>
                </div>
              </div>
            );
            if (b.type === 'stats' && b.items) return (
              <div key={i} style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', margin: '24px 0' }}>
                {b.items.map((st: any, idx: number) => (
                  <div key={idx} style={{ backgroundColor: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '12px', padding: '16px' }}>
                    <div style={{ fontSize: '28px', fontWeight: 300, letterSpacing: '-.02em', color: 'var(--text)' }}>{st.v}</div>
                    <div style={{ fontSize: '14px', fontStyle: 'italic', color: 'var(--text-dim)', marginTop: '2px' }}>{st.k}</div>
                    <div className="sg-mono" style={{ fontSize: '10.5px', color: st.dc, marginTop: '8px' }}>{st.d}</div>
                  </div>
                ))}
              </div>
            );
            if (b.type === 'chart') return (
              <figure key={i} style={{ margin: '26px 0', backgroundColor: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '14px', padding: '20px 20px 16px' }}>
                <div className="sg-mono" style={{ fontSize: '10px', letterSpacing: '.12em', textTransform: 'uppercase', color: 'var(--text-faint)', marginBottom: '18px' }}>{b.title}</div>
                <div style={{ display: 'flex', alignItems: 'flex-end', gap: '14px', height: '150px', paddingBottom: '8px', borderBottom: '1px solid var(--border)' }}>
                  {b.data?.map((bar, idx) => {
                    const heightPct = (bar.v / 100) * 100; // max value is ~100
                    return (
                      <div key={idx} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'flex-end', height: '100%', gap: '8px' }}>
                        <span className="sg-mono" style={{ fontSize: '12px', color: 'var(--text)' }}>{bar.v}</span>
                        <div style={{ width: '100%', backgroundColor: 'var(--accent)', borderRadius: '4px 4px 0 0', height: `${heightPct}%` }}></div>
                      </div>
                    );
                  })}
                </div>
                <div style={{ display: 'flex', gap: '14px', marginTop: '8px' }}>
                  {b.data?.map((bar, idx) => (
                    <span key={idx} className="sg-mono" style={{ flex: 1, textAlign: 'center', fontSize: '11px', color: 'var(--text-dim)' }}>{bar.label}</span>
                  ))}
                </div>
                <figcaption style={{ fontSize: '13.5px', fontStyle: 'italic', color: 'var(--text-dim)', marginTop: '14px' }}>{b.caption}</figcaption>
              </figure>
            );
            if (b.type === 'table' && b.rows) return (
              <div key={i} style={{ margin: '24px 0', border: '1px solid var(--border-strong)', borderRadius: '12px', overflow: 'hidden' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'var(--font-mono)', fontSize: '13px' }}>
                  <thead>
                    <tr>
                      {b.head?.map((h, idx) => (
                        <th key={idx} style={{ textAlign: 'left', padding: '11px 14px', backgroundColor: 'var(--surface-3)', fontSize: '10px', letterSpacing: '.08em', textTransform: 'uppercase', fontWeight: 500, color: 'var(--text-dim)', borderBottom: '1px solid var(--border)' }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {b.rows.map((row, idx) => (
                      <tr key={idx}>
                        {row.map((cell: any, cIdx: any) => (
                          <td key={cIdx} style={{ padding: '11px 14px', borderBottom: idx === b.rows!.length - 1 ? 'none' : '1px solid var(--border)', color: 'var(--text)' }}>{cell}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            );
            if (b.type === 'image') return (
              <figure key={i} style={{ margin: '26px 0' }}>
                <div style={{ height: '220px', border: '1px solid var(--border-strong)', borderRadius: '14px', backgroundImage: 'repeating-linear-gradient(45deg, var(--surface-2), var(--surface-2) 11px, var(--surface) 11px, var(--surface) 22px)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <span className="sg-mono" style={{ fontSize: '11px', letterSpacing: '.1em', textTransform: 'uppercase', color: 'var(--text-faint)', backgroundColor: 'var(--surface)', padding: '6px 12px', borderRadius: '8px', border: '1px solid var(--border)' }}>{b.caption}</span>
                </div>
              </figure>
            );
            if (b.type === 'quote') return (
              <blockquote key={i} style={{ margin: '28px 0', padding: '6px 0 6px 22px', borderLeft: '3px solid var(--accent)', fontSize: '22px', fontWeight: 300, fontStyle: 'italic', lineHeight: 1.5, color: 'var(--text)' }}>
                {b.text}
                <footer className="sg-mono" style={{ fontSize: '11px', fontStyle: 'normal', color: 'var(--text-faint)', letterSpacing: '.06em', textTransform: 'uppercase', marginTop: '14px' }}>{b.cite}</footer>
              </blockquote>
            );
            if (b.type === 'refs' && b.items) return (
              <ul key={i} style={{ listStyle: 'none', margin: '14px 0 0', padding: 0, display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {b.items.map((ref: any, idx: number) => (
                  <li key={idx} style={{ display: 'flex', gap: '12px', fontSize: '15px', lineHeight: 1.5 }}>
                    <span className="sg-mono" style={{ flexShrink: 0, fontSize: '11px', padding: '2px 7px', height: 'fit-content', borderRadius: '5px', backgroundColor: 'var(--surface-3)', color: 'var(--accent-2)' }}>{ref.k}</span>
                    <span>
                      <span style={{ color: 'var(--text)' }}>{ref.t}</span>{' '}
                      <a href={ref.href} target="_blank" rel="noopener noreferrer" className="sg-mono" style={{ fontSize: '12px', color: 'var(--accent-2)' }}>{ref.u}</a>
                    </span>
                  </li>
                ))}
              </ul>
            );
            return null;
          })}
        </article>
      </div>

      {/* Collapsed Chat Rail */}
      {chatCollapsed && (
        <button
          onClick={toggleChatCollapsed}
          title="Show chat"
          style={{ width: '56px', flexShrink: 0, border: 'none', borderLeft: '1px solid var(--border)', backgroundColor: 'var(--surface)', display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '18px 0 20px', gap: '16px', cursor: 'pointer', color: 'var(--text-dim)' }}
        >
          <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: '36px', height: '36px', border: '1px solid var(--border)', backgroundColor: 'var(--surface-2)', borderRadius: '10px' }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><polyline points="15 18 9 12 15 6" /></svg>
          </span>
          <span style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'flex-start', gap: '10px', paddingTop: '6px', color: 'var(--text-faint)' }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /></svg>
            <span className="sg-mono" style={{ fontSize: '11px', writingMode: 'vertical-rl', textOrientation: 'mixed', letterSpacing: '.16em', textTransform: 'uppercase' }}>{report.chats.length} chats</span>
          </span>
        </button>
      )}

      {/* Expanded Chat Panel */}
      {!chatCollapsed && (
        <div style={{ width: '400px', flexShrink: 0, borderLeft: '1px solid var(--border)', backgroundColor: 'var(--surface)', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
          <div style={{ height: '72px', flexShrink: 0, padding: '0 12px 0 16px', borderBottom: '1px solid var(--border)', display: 'flex', gap: '8px', alignItems: 'center' }}>
            <button
              onClick={toggleChatCollapsed}
              title="Hide chat"
              style={{ flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', width: '38px', height: '38px', border: '1px solid var(--border)', backgroundColor: 'var(--surface-2)', color: 'var(--text-dim)', borderRadius: '11px', cursor: 'pointer' }}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><polyline points="9 18 15 12 9 6" /></svg>
            </button>
            <div style={{ position: 'relative', flex: 1, minWidth: 0 }}>
              <button
                onClick={toggleThreadMenu}
                style={{ display: 'flex', alignItems: 'center', gap: '9px', width: '100%', padding: '8px 10px', border: '1px solid var(--border)', backgroundColor: 'var(--surface-2)', borderRadius: '11px', cursor: 'pointer', textAlign: 'left', color: 'var(--text)' }}
              >
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--text-dim)" strokeWidth="1.8" style={{ flexShrink: 0 }}><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /></svg>
                <span style={{ flex: 1, minWidth: 0 }}>
                  <span style={{ display: 'block', fontSize: '14px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{activeChat?.title}</span>
                  <span className="sg-mono" style={{ display: 'block', fontSize: '10px', color: 'var(--text-faint)', marginTop: '1px' }}>{chatPositionLabel}</span>
                </span>
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ opacity: 0.5, flexShrink: 0 }}><polyline points="6 9 12 15 18 9" /></svg>
              </button>
              
              {threadMenuOpen && (
                <div className="animate-sg-pop" style={{ position: 'absolute', top: 'calc(100% + 6px)', left: 0, right: 0, backgroundColor: 'var(--surface)', border: '1px solid var(--border-strong)', borderRadius: '13px', boxShadow: 'var(--shadow)', padding: '6px', zIndex: 50 }}>
                  <div className="sg-mono" style={{ padding: '7px 9px 5px', fontSize: '9.5px', letterSpacing: '.12em', textTransform: 'uppercase', color: 'var(--text-faint)' }}>{report.chats.length} chats in this research</div>
                  {report.chats.map((c) => (
                    <button
                      key={c.id}
                      onClick={() => { setActiveChatId(c.id); setThreadMenuOpen(false); }}
                      style={{ display: 'flex', alignItems: 'center', gap: '8px', width: '100%', padding: '8px 9px', border: 'none', borderRadius: '8px', cursor: 'pointer', fontFamily: 'var(--font-mono)', fontSize: '12.5px', backgroundColor: activeChatId === c.id ? 'var(--accent-soft)' : 'transparent', color: 'var(--text)' }}
                    >
                      <span style={{ flex: 1, textAlign: 'left', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.title}</span>
                      {activeChatId === c.id && <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--accent-2)" strokeWidth="2.4"><polyline points="20 6 9 17 4 12" /></svg>}
                    </button>
                  ))}
                  <button
                    onClick={() => { console.log('New chat'); setThreadMenuOpen(false); }}
                    style={{ display: 'flex', alignItems: 'center', gap: '8px', width: '100%', padding: '9px', border: 'none', borderTop: '1px solid var(--border)', marginTop: '4px', backgroundColor: 'transparent', color: 'var(--accent-2)', borderRadius: '8px', cursor: 'pointer', fontFamily: 'var(--font-mono)', fontSize: '12.5px' }}
                  >
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>New chat on this report
                  </button>
                </div>
              )}
            </div>
          </div>

          <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', padding: '20px 18px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {chatMessages.map((m, i) => (
              <div key={i} style={{ alignSelf: m.isUser ? 'flex-end' : 'flex-start', maxWidth: '85%' }}>
                <div className="sg-mono" style={{ fontSize: '9.5px', letterSpacing: '.1em', textTransform: 'uppercase', color: 'var(--text-faint)', marginBottom: '6px', textAlign: m.isUser ? 'right' : 'left' }}>
                  {m.who}
                </div>
                <div style={{ 
                  padding: m.isUser ? '12px 16px' : '4px 0', 
                  backgroundColor: m.isUser ? 'var(--surface-3)' : 'transparent',
                  border: 'none',
                  borderRadius: '16px',
                  borderTopRightRadius: m.isUser ? '4px' : '16px',
                  borderTopLeftRadius: !m.isUser ? '4px' : '16px',
                  fontSize: '15px',
                  lineHeight: 1.5,
                  color: 'var(--text)'
                }}>
                  {m.text}
                </div>
              </div>
            ))}
          </div>

          <div style={{ flexShrink: 0, padding: '12px 16px 16px' }}>
            <form onSubmit={handleReportSend} style={{ backgroundColor: 'var(--surface-2)', border: '1px solid var(--border-strong)', borderRadius: '16px', position: 'relative' }}>
              <textarea
                value={reportQuery}
                onChange={(e) => setReportQuery(e.target.value)}
                onKeyDown={handleReportKeyDown}
                rows={1}
                placeholder="Ask a follow-up about this report…"
                style={{ width: '100%', resize: 'none', border: 'none', outline: 'none', background: 'transparent', color: 'var(--text)', fontFamily: 'var(--font-serif)', fontSize: '16px', lineHeight: 1.5, maxHeight: '120px', padding: '13px 14px 6px' }}
              />
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '2px 10px 10px' }}>
                <div style={{ position: 'relative' }}>
                  <button
                    type="button"
                    onClick={toggleRModelMenu}
                    style={{ display: 'flex', alignItems: 'center', gap: '6px', height: '28px', padding: '0 10px', border: '1px solid var(--border)', backgroundColor: 'var(--surface)', borderRadius: '8px', cursor: 'pointer', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', fontSize: '11.5px' }}
                  >
                    <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: modelDot }}></span>
                    {modelName}
                    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ opacity: 0.5 }}><polyline points="6 9 12 15 18 9" /></svg>
                  </button>
                  {rModelMenuOpen && (
                    <div className="animate-sg-pop" style={{ position: 'absolute', bottom: 'calc(100% + 8px)', left: 0, width: '230px', maxHeight: '280px', overflowY: 'auto', backgroundColor: 'var(--surface)', border: '1px solid var(--border-strong)', borderRadius: '13px', boxShadow: 'var(--shadow)', padding: '6px', zIndex: 50 }}>
                      {MODELS.map((g) => (
                        <div key={g.group}>
                          <div className="sg-mono" style={{ padding: '8px 9px 4px', fontSize: '9.5px', letterSpacing: '.12em', textTransform: 'uppercase', color: 'var(--text-faint)', display: 'flex', alignItems: 'center', gap: '7px' }}>
                            <span style={{ width: '7px', height: '7px', borderRadius: '50%', backgroundColor: g.dot }}></span>
                            {g.group}
                          </div>
                          {g.items.map((mi) => (
                            <button
                              key={mi.id}
                              type="button"
                              onClick={() => { setModelId(mi.id); setRModelMenuOpen(false); }}
                              style={{ display: 'flex', alignItems: 'center', gap: '8px', width: '100%', padding: '8px 9px', border: 'none', borderRadius: '8px', cursor: 'pointer', fontFamily: 'var(--font-mono)', fontSize: '12.5px', backgroundColor: modelId === mi.id ? 'var(--accent-soft)' : 'transparent', color: 'var(--text)' }}
                            >
                              <span style={{ flex: 1, textAlign: 'left' }}>{mi.name}</span>
                              {modelId === mi.id && <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--accent-2)" strokeWidth="2.4"><polyline points="20 6 9 17 4 12" /></svg>}
                            </button>
                          ))}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                
                <button
                  type="submit"
                  title="Send"
                  disabled={!reportQuery.trim()}
                  style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', justifyContent: 'center', width: '28px', height: '28px', borderRadius: '8px', border: 'none', backgroundColor: reportQuery.trim() ? 'var(--accent)' : 'var(--surface-3)', color: reportQuery.trim() ? '#fff' : 'var(--text-faint)', cursor: reportQuery.trim() ? 'pointer' : 'default', transition: 'background-color 0.2s, color 0.2s' }}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="12" y1="19" x2="12" y2="5" /><polyline points="5 12 12 5 19 12" /></svg>
                </button>
              </div>
              
              {(threadMenuOpen || rModelMenuOpen) && <div onClick={closeMenus} style={{ position: 'fixed', inset: 0, zIndex: 40 }}></div>}
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

'use client';

import Image from 'next/image';
import { useAppStore } from '@/store/app-store';
import { REPORTS, STANDALONE_CHATS } from '@/lib/dummy-data';
import { AppLogoMark } from '@/components/app-logo';

export function Sidebar() {
  const { sidebarOpen, toggleSidebar, activeReportId, activeChatId, view, setView, setActiveReportId, setActiveChatId, setMode } = useAppStore();

  const handleNewResearch = () => {
    setView('grid');
    setMode('research');
  };

  const handleOpenReport = (id: string, chatId?: string) => {
    const report = REPORTS.find((r) => r.id === id);
    if (!report) return;
    const cid = chatId || (report.chats[0]?.id);
    setActiveReportId(id);
    setActiveChatId(cid);
    setView('report');
  };

  const handleOpenChat = (id: string) => {
    setActiveChatId(id);
    setView('chat');
  };

  return (
    <aside
      data-screen-label="Sidebar"
      style={{
        width: sidebarOpen ? '264px' : '62px',
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        backgroundColor: 'var(--surface)',
        borderRight: '1px solid var(--border)',
        transition: 'width 0.2s',
        flexShrink: 0,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '9px', height: '58px', padding: '0 12px 0 14px', borderBottom: '1px solid var(--border)', flexShrink: 0 }}>
        {sidebarOpen ? (
          <>
            <AppLogoMark width={32} height={32} />
            <span style={{ fontSize: '18px', fontWeight: 500, letterSpacing: '-.01em', whiteSpace: 'nowrap' }}>Singularity</span>
            <button
              onClick={toggleSidebar}
              title="Collapse sidebar"
              style={{
                marginLeft: 'auto', flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
                width: '34px', height: '34px', border: '1px solid var(--border)', backgroundColor: 'var(--surface-2)', color: 'var(--text-dim)', borderRadius: '9px', cursor: 'pointer',
              }}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="15 18 9 12 15 6" /></svg>
            </button>
          </>
        ) : (
          <button
            onClick={toggleSidebar}
            title="Expand sidebar"
            className="group"
            style={{
              position: 'relative', width: '38px', height: '38px', margin: '0 auto', flexShrink: 0, border: 'none', background: 'transparent', padding: 0, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center'
            }}
          >
            <div className="transition-opacity duration-150 group-hover:opacity-0" style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <AppLogoMark width={38} height={38} />
            </div>
            <span className="opacity-0 transition-opacity duration-150 group-hover:opacity-100 absolute inset-0 flex items-center justify-center text-[var(--text)] border border-[var(--border)] bg-[var(--surface-2)] rounded-[8px]">
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="9 18 15 12 9 6" /></svg>
            </span>
          </button>
        )}
      </div>

      <div style={{ padding: '12px', flexShrink: 0 }}>
        <button
          onClick={handleNewResearch}
          style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', width: '100%', height: '40px', border: '1px solid var(--border-strong)',
            backgroundColor: 'var(--surface-2)', color: 'var(--text)', borderRadius: '10px', cursor: 'pointer', fontFamily: 'var(--font-mono)', fontSize: '13px', fontWeight: 500,
          }}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>
          {sidebarOpen && <span style={{ whiteSpace: 'nowrap' }}>New research</span>}
        </button>
      </div>

      {sidebarOpen && (
        <div className="sg-mono" style={{ padding: '6px 18px 6px', fontSize: '10px', letterSpacing: '.14em', textTransform: 'uppercase', color: 'var(--text-faint)' }}>Research</div>
      )}
      
      <nav style={{ flex: 1, minHeight: 0, overflowY: 'auto', padding: '2px 8px 12px', display: 'flex', flexDirection: 'column', gap: '2px' }}>
        {REPORTS.map((r) => {
          const active = r.id === activeReportId && view === 'report';
          const expanded = active && sidebarOpen;
          return (
            <div key={r.id}>
              <button
                onClick={() => handleOpenReport(r.id)}
                title={r.title}
                style={{
                  display: 'flex', alignItems: 'center', gap: '9px', width: '100%', padding: '9px 8px', border: 'none', borderRadius: '9px', cursor: 'pointer', textAlign: 'left',
                  backgroundColor: active ? 'var(--accent-soft)' : 'transparent', color: 'var(--text-dim)', justifyContent: sidebarOpen ? 'flex-start' : 'center',
                }}
              >
                <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: '22px', flexShrink: 0, color: 'var(--text-faint)' }}>
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /></svg>
                </span>
                {sidebarOpen && (
                  <>
                    <span style={{ flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: '13.5px' }}>{r.title}</span>
                    <span className="sg-mono" style={{ fontSize: '10px', color: 'var(--text-faint)', flexShrink: 0 }}>{r.chats.length}</span>
                  </>
                )}
              </button>
              {expanded && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1px', margin: '1px 0 4px 22px', paddingLeft: '8px', borderLeft: '1px solid var(--border)' }}>
                  {r.chats.map((c) => {
                    const csel = active && c.id === activeChatId;
                    return (
                      <button
                        key={c.id}
                        onClick={() => handleOpenReport(r.id, c.id)}
                        title={c.title}
                        style={{
                          display: 'flex', alignItems: 'center', gap: '7px', padding: '6px 8px', border: 'none', background: 'transparent', borderRadius: '7px', cursor: 'pointer',
                          fontSize: '12.5px', textAlign: 'left', color: csel ? 'var(--accent-2)' : 'var(--text-dim)'
                        }}
                      >
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" style={{ flexShrink: 0, opacity: 0.7 }}><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /></svg>
                        <span style={{ flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.title}</span>
                      </button>
                    );
                  })}
                  <button onClick={() => handleOpenReport(r.id)} style={{ display: 'flex', alignItems: 'center', gap: '7px', padding: '6px 8px', border: 'none', background: 'transparent', color: 'var(--text-faint)', borderRadius: '7px', cursor: 'pointer', fontSize: '12px', textAlign: 'left' }} className="sg-mono">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>New chat
                  </button>
                </div>
              )}
            </div>
          );
        })}

        {sidebarOpen && (
          <div className="sg-mono" style={{ padding: '14px 10px 6px', fontSize: '10px', letterSpacing: '.14em', textTransform: 'uppercase', color: 'var(--text-faint)' }}>Chats</div>
        )}
        
        {STANDALONE_CHATS.map((c) => {
          const active = c.id === activeChatId && view === 'chat';
          return (
            <button
              key={c.id}
              onClick={() => handleOpenChat(c.id)}
              title={c.title}
              style={{
                display: 'flex', alignItems: 'center', gap: '9px', width: '100%', padding: '9px 8px', border: 'none', borderRadius: '9px', cursor: 'pointer', textAlign: 'left',
                backgroundColor: active ? 'var(--accent-soft)' : 'transparent', color: active ? 'var(--text)' : 'var(--text-dim)', justifyContent: sidebarOpen ? 'flex-start' : 'center',
              }}
            >
              <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: '22px', flexShrink: 0, color: 'var(--text-faint)' }}>
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /></svg>
              </span>
              {sidebarOpen && (
                <span style={{ flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: '13.5px' }}>{c.title}</span>
              )}
            </button>
          );
        })}
      </nav>
    </aside>
  );
}

'use client';

import { useEffect, useRef, useState } from 'react';
import { useAppStore } from '@/store/app-store';
import { useWorkspace } from '@/components/workspace-provider';
import { AppLogoMark } from '@/components/app-logo';

const CHATS_PAGE_SIZE = 20;
const REPORTS_PAGE_SIZE = 5;

function KebabIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="8" cy="3" r="1.4" fill="currentColor" />
      <circle cx="8" cy="8" r="1.4" fill="currentColor" />
      <circle cx="8" cy="13" r="1.4" fill="currentColor" />
    </svg>
  );
}

function TrashIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M2.5 4.5H13.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
      <path d="M6 4.5V3a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v1.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
      <path d="M4.5 4.5L5 13a1 1 0 0 0 1 1h4a1 1 0 0 0 1-1l.5-8.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M6.5 7v4M9.5 7v4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
    </svg>
  );
}

function FileIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" y1="13" x2="8" y2="13" />
      <line x1="16" y1="17" x2="8" y2="17" />
      <line x1="10" y1="9" x2="8" y2="9" />
    </svg>
  );
}

function ChatIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  );
}

function SectionChevron({ collapsed }: { collapsed: boolean }) {
  return (
    <svg
      width="10"
      height="10"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      style={{ flexShrink: 0, transform: collapsed ? 'rotate(-90deg)' : 'rotate(0deg)', transition: 'transform 0.15s ease' }}
    >
      <polyline points="6 9 12 15 18 9" />
    </svg>
  );
}

export function Sidebar() {
  const { sidebarOpen, toggleSidebar, activeReportId, activeChatId, view, setView, setActiveReportId, setActiveChatId, setMode } = useAppStore();
  const { reports, chats, deleteChat, deleteReport } = useWorkspace();
  const [isHovered, setIsHovered] = useState(false);
  const [chatMenuOpenId, setChatMenuOpenId] = useState<string | null>(null);
  const [hoveredChatId, setHoveredChatId] = useState<string | null>(null);
  const [chatMenuAnchor, setChatMenuAnchor] = useState<{ top: number; right: number } | null>(null);
  const [reportMenuOpenId, setReportMenuOpenId] = useState<string | null>(null);
  const [hoveredReportId, setHoveredReportId] = useState<string | null>(null);
  const [reportMenuAnchor, setReportMenuAnchor] = useState<{ top: number; right: number } | null>(null);
  const [visibleChatCount, setVisibleChatCount] = useState(CHATS_PAGE_SIZE);
  const [visibleReportCount, setVisibleReportCount] = useState(REPORTS_PAGE_SIZE);
  const [researchCollapsed, setResearchCollapsed] = useState(false);
  const [chatsCollapsed, setChatsCollapsed] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const reportMenuRef = useRef<HTMLDivElement>(null);
  const directChats = chats.filter((chat) => !chat.report_id);

  useEffect(() => {
    if (!chatMenuOpenId) return;
    const onClickAway = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) setChatMenuOpenId(null);
    };
    document.addEventListener('mousedown', onClickAway);
    return () => document.removeEventListener('mousedown', onClickAway);
  }, [chatMenuOpenId]);

  useEffect(() => {
    if (!reportMenuOpenId) return;
    const onClickAway = (event: MouseEvent) => {
      if (reportMenuRef.current && !reportMenuRef.current.contains(event.target as Node)) setReportMenuOpenId(null);
    };
    document.addEventListener('mousedown', onClickAway);
    return () => document.removeEventListener('mousedown', onClickAway);
  }, [reportMenuOpenId]);

  const openReport = (id: string) => { setActiveReportId(id); setView('report'); };
  const openChat = (id: string) => { setActiveChatId(id); setView('chat'); };
  const onDeleteChat = async (id: string) => {
    setChatMenuOpenId(null);
    await deleteChat(id);
    if (activeChatId === id) { setActiveChatId(null); setView('grid'); }
  };
  const onDeleteReport = async (id: string) => {
    setReportMenuOpenId(null);
    await deleteReport(id);
    if (activeReportId === id) { setActiveReportId(null); setView('grid'); }
  };

  return <aside style={{ width: sidebarOpen ? '264px' : '62px', display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: 'var(--surface)', borderRight: '1px solid var(--border)', transition: 'width .2s', flexShrink: 0 }}>
    <div
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      style={{ display: 'flex', alignItems: 'center', gap: '9px', height: '58px', padding: sidebarOpen ? '0 12px 0 14px' : '0', justifyContent: sidebarOpen ? 'flex-start' : 'center', borderBottom: '1px solid var(--border)', flexShrink: 0 }}
    >
      {sidebarOpen ? (
        <>
          <AppLogoMark width={32} height={32} />
          <span style={{ fontSize: '18px', fontWeight: 600 }}>Singularity</span>
          <button onClick={toggleSidebar} title="Collapse sidebar" style={{ marginLeft: 'auto', width: '30px', height: '30px', border: '1px solid var(--border)', background: 'var(--surface-2)', borderRadius: '8px', cursor: 'pointer', color: 'var(--text)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            ‹
          </button>
        </>
      ) : (
        isHovered ? (
          <button onClick={toggleSidebar} title="Expand sidebar" style={{ width: '32px', height: '32px', border: '1px solid var(--border)', background: 'var(--surface-2)', borderRadius: '8px', cursor: 'pointer', color: 'var(--text)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            ›
          </button>
        ) : (
          <AppLogoMark width={32} height={32} />
        )
      )}
    </div>
    <div style={{ padding: '12px' }}>
      <button onClick={() => { setView('grid'); setMode('chat'); }} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: '100%', height: '40px', border: '1px solid var(--border-strong)', background: 'var(--surface-2)', borderRadius: '10px', cursor: 'pointer', color: 'var(--text)', paddingTop: '2px', fontSize: '13.5px' }}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginRight: sidebarOpen ? '6px' : '0' }}><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>
        {sidebarOpen && 'New Chat'}
      </button>
    </div>
    <nav style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, padding: '2px 8px 12px' }}>
      <div style={{ flexShrink: 0, overflowY: 'auto', maxHeight: '40%' }}>
        {sidebarOpen && (
          <button
            onClick={() => setResearchCollapsed((value) => !value)}
            className="sg-mono"
            style={{ display: 'flex', alignItems: 'center', gap: '6px', width: '100%', padding: '6px 10px', border: 'none', background: 'transparent', cursor: 'pointer', fontSize: '10px', color: 'var(--text-faint)', textAlign: 'left', letterSpacing: 'inherit' }}
          >
            <SectionChevron collapsed={researchCollapsed} />
            RESEARCH
          </button>
        )}
        {!(sidebarOpen && researchCollapsed) && reports.slice(0, visibleReportCount).map((report) => (
          <div
            key={report.id}
            style={{ position: 'relative', display: 'flex', alignItems: 'center', marginBottom: '4px' }}
            onMouseEnter={() => setHoveredReportId(report.id)}
            onMouseLeave={() => setHoveredReportId((current) => (current === report.id ? null : current))}
          >
            <button
              onClick={() => openReport(report.id)}
              title={report.title || 'Untitled report'}
              style={{ display: 'flex', alignItems: 'center', justifyContent: sidebarOpen ? 'flex-start' : 'center', gap: '8px', width: '100%', textAlign: 'left', padding: '9px 8px', paddingRight: sidebarOpen ? '30px' : '8px', border: 'none', borderRadius: '8px', cursor: 'pointer', background: view === 'report' && activeReportId === report.id ? 'var(--accent-soft)' : (hoveredReportId === report.id ? 'var(--surface-2)' : 'transparent'), transition: 'background 0.2s ease', color: 'var(--text-dim)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: '13.5px' }}
            >
              <FileIcon />
              {sidebarOpen && <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{report.title || 'Untitled report'}</span>}
            </button>
            {sidebarOpen && (hoveredReportId === report.id || reportMenuOpenId === report.id) && (
              <button
                onClick={(event) => {
                  event.stopPropagation();
                  if (reportMenuOpenId === report.id) { setReportMenuOpenId(null); return; }
                  const rect = event.currentTarget.getBoundingClientRect();
                  setReportMenuAnchor({ top: rect.bottom + 4, right: window.innerWidth - rect.right });
                  setReportMenuOpenId(report.id);
                }}
                title="Report options"
                style={{ position: 'absolute', right: '4px', width: '24px', height: '24px', border: 'none', background: 'transparent', borderRadius: '6px', cursor: 'pointer', color: 'var(--text-dim)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
              >
                <KebabIcon />
              </button>
            )}
          </div>
        ))}
        {sidebarOpen && !researchCollapsed && reports.length === 0 && <div style={{ padding: '4px 10px', fontSize: '13px', color: 'var(--text-faint)' }}>No Research Work</div>}
        {sidebarOpen && !researchCollapsed && reports.length > visibleReportCount && (
          <button
            onClick={() => setVisibleReportCount((count) => count + REPORTS_PAGE_SIZE)}
            style={{ width: '100%', textAlign: 'left', padding: '9px 10px', border: 'none', borderRadius: '8px', cursor: 'pointer', background: 'transparent', color: 'var(--text-faint)', fontSize: '13px' }}
          >
            Show More
          </button>
        )}
      </div>
      {sidebarOpen && (
        <button
          onClick={() => setChatsCollapsed((value) => !value)}
          className="sg-mono"
          style={{ display: 'flex', alignItems: 'center', gap: '6px', width: '100%', padding: '14px 10px 6px', border: 'none', background: 'transparent', cursor: 'pointer', fontSize: '10px', color: 'var(--text-faint)', textAlign: 'left', letterSpacing: 'inherit', flexShrink: 0 }}
        >
          <SectionChevron collapsed={chatsCollapsed} />
          CHATS
        </button>
      )}
      <div style={{ flex: 1, minHeight: 0, overflowY: 'auto' }}>
        {!(sidebarOpen && chatsCollapsed) && directChats.slice(0, visibleChatCount).map((chat) => (
          <div
            key={chat.id}
            style={{ position: 'relative', display: 'flex', alignItems: 'center', marginBottom: '4px' }}
            onMouseEnter={() => setHoveredChatId(chat.id)}
            onMouseLeave={() => setHoveredChatId((current) => (current === chat.id ? null : current))}
          >
            <button
              onClick={() => openChat(chat.id)}
              title={chat.title || 'New chat'}
              style={{ display: 'flex', alignItems: 'center', justifyContent: sidebarOpen ? 'flex-start' : 'center', gap: '8px', width: '100%', textAlign: 'left', padding: '9px 8px', paddingRight: sidebarOpen ? '30px' : '8px', border: 'none', borderRadius: '8px', cursor: 'pointer', background: view === 'chat' && activeChatId === chat.id ? 'var(--accent-soft)' : (hoveredChatId === chat.id ? 'var(--surface-2)' : 'transparent'), transition: 'background 0.2s ease', color: 'var(--text-dim)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: '13.5px' }}
            >
              <ChatIcon />
              {sidebarOpen && <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{chat.title || 'New chat'}</span>}
            </button>
            {sidebarOpen && (hoveredChatId === chat.id || chatMenuOpenId === chat.id) && (
              <button
                onClick={(event) => {
                  event.stopPropagation();
                  if (chatMenuOpenId === chat.id) { setChatMenuOpenId(null); return; }
                  const rect = event.currentTarget.getBoundingClientRect();
                  setChatMenuAnchor({ top: rect.bottom + 4, right: window.innerWidth - rect.right });
                  setChatMenuOpenId(chat.id);
                }}
                title="Chat options"
                style={{ position: 'absolute', right: '4px', width: '24px', height: '24px', border: 'none', background: 'transparent', borderRadius: '6px', cursor: 'pointer', color: 'var(--text-dim)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
              >
                <KebabIcon />
              </button>
            )}
          </div>
        ))}
        {sidebarOpen && !chatsCollapsed && directChats.length === 0 && <div style={{ padding: '4px 10px', fontSize: '13px', color: 'var(--text-faint)' }}>No Chats</div>}
        {sidebarOpen && !chatsCollapsed && directChats.length > visibleChatCount && (
          <button
            onClick={() => setVisibleChatCount((count) => count + CHATS_PAGE_SIZE)}
            style={{ width: '100%', textAlign: 'left', padding: '9px 10px', border: 'none', borderRadius: '8px', cursor: 'pointer', background: 'transparent', color: 'var(--text-faint)', fontSize: '13px' }}
          >
            Show More
          </button>
        )}
      </div>
    </nav>
    {reportMenuOpenId && reportMenuAnchor && (
      <div
        ref={reportMenuRef}
        style={{ position: 'fixed', top: reportMenuAnchor.top, right: reportMenuAnchor.right, zIndex: 50, background: 'var(--surface-2)', border: '1px solid var(--border)', borderRadius: '8px', boxShadow: '0 4px 16px rgba(0,0,0,0.2)', minWidth: '140px', overflow: 'hidden' }}
      >
        <button
          onClick={(event) => { event.stopPropagation(); void onDeleteReport(reportMenuOpenId).catch(() => undefined); }}
          style={{ width: '100%', display: 'flex', alignItems: 'center', gap: '8px', textAlign: 'left', padding: '9px 12px', border: 'none', background: 'transparent', cursor: 'pointer', color: 'var(--danger, #d94a38)', fontSize: '13px', lineHeight: 1 }}
        >
          <span style={{ display: 'inline-flex', flexShrink: 0 }}><TrashIcon /></span>
          <span>Delete report</span>
        </button>
      </div>
    )}
    {chatMenuOpenId && chatMenuAnchor && (
      <div
        ref={menuRef}
        style={{ position: 'fixed', top: chatMenuAnchor.top, right: chatMenuAnchor.right, zIndex: 50, background: 'var(--surface-2)', border: '1px solid var(--border)', borderRadius: '8px', boxShadow: '0 4px 16px rgba(0,0,0,0.2)', minWidth: '140px', overflow: 'hidden' }}
      >
        <button
          onClick={(event) => { event.stopPropagation(); void onDeleteChat(chatMenuOpenId).catch(() => undefined); }}
          style={{ width: '100%', display: 'flex', alignItems: 'center', gap: '8px', textAlign: 'left', padding: '9px 12px', border: 'none', background: 'transparent', cursor: 'pointer', color: 'var(--danger, #d94a38)', fontSize: '13px', lineHeight: 1 }}
        >
          <span style={{ display: 'inline-flex', flexShrink: 0 }}><TrashIcon /></span>
          <span>Delete chat</span>
        </button>
      </div>
    )}
  </aside>;
}

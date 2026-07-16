'use client';

import { FormEvent, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { useAppStore } from '@/store/app-store';
import { useWorkspace } from '@/components/workspace-provider';
import { Markdown } from '@/components/ui/markdown';
import { useIsMobile } from '@/lib/use-media-query';

export function ReportView() {
  const { activeReportId, activeChatId, setActiveChatId, setActiveRunId, setView, chatCollapsed, toggleChatCollapsed, mobileReportChatOpen, setMobileReportChatOpen } = useAppStore();
  const isMobile = useIsMobile();
  const { reports, runs, chats, messages, reportContent, runActivity, loadReport, loadMessages, createAndSendChat, sendChat, cancelResearch, activeCredential, availableModels, modelsLoading, streamingChatIds } = useWorkspace();
  const [query, setQuery] = useState('');
  const [sending, setSending] = useState(false);
  // A report-chat draft is deliberately client-only. Clicking New must show a
  // blank conversation without adding an empty chat to the sidebar/database;
  // the first submitted message creates the real, report-linked chat.
  const [draft, setDraft] = useState<{ reportId: string; modelId: string | null } | null>(null);
  const [openMenu, setOpenMenu] = useState<'model' | 'thread' | null>(null);
  const formRef = useRef<HTMLFormElement>(null);
  const chatScrollRef = useRef<HTMLDivElement>(null);
  const report = reports.find((item) => item.id === activeReportId);
  const run = runs.find((item) => item.report_id === activeReportId);
  const reportChats = chats.filter((item) => item.report_id === activeReportId);
  const draftChat = Boolean(activeReportId && draft?.reportId === activeReportId);
  const draftModelId = draftChat ? draft?.modelId ?? null : null;
  const selectedChat = draftChat ? undefined : reportChats.find((item) => item.id === activeChatId) ?? reportChats[0];
  const turns = selectedChat ? messages[selectedChat.id] ?? [] : [];
  const isStreaming = !!selectedChat && streamingChatIds.includes(selectedChat.id);
  const effectiveDraftModelId = draftModelId
    ?? activeCredential?.default_model_id
    ?? availableModels[0]?.id
    ?? null;
  const draftModelLabel = modelsLoading
    ? 'Loading models…'
    : availableModels.find((model) => model.id === effectiveDraftModelId)?.id
      ?? effectiveDraftModelId
      ?? 'Select a model';

  useEffect(() => { if (activeReportId) void loadReport(activeReportId); }, [activeReportId, loadReport]);
  useEffect(() => {
    if (!draftChat && selectedChat) {
      setActiveChatId(selectedChat.id);
      void loadMessages(selectedChat.id);
    }
  }, [draftChat, selectedChat, setActiveChatId, loadMessages]);

  // Report-context chats use the same SSE stream as regular chats. Keep their
  // narrower sidebar pinned while a reply is active so the pending state and
  // every token remain visible after the user sends a question.
  const lastTurn = turns.at(-1);
  const followKey = `${isStreaming}:${turns.length}:${lastTurn?.content.length ?? 0}`;
  useLayoutEffect(() => {
    if (!isStreaming) return;
    const el = chatScrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [followKey, isStreaming, selectedChat?.id]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!query.trim() || !activeReportId || sending) return;
    setSending(true);
    try {
      if (selectedChat) await sendChat(selectedChat.id, query.trim());
      else {
        const chat = await createAndSendChat(query.trim(), activeReportId, effectiveDraftModelId ?? undefined);
        setActiveChatId(chat.id);
        setDraft(null);
      }
      setQuery('');
    } catch {
      // The shared error dialog already contains the user-facing failure.
    } finally { setSending(false); }
  };

  const handleNewChat = () => {
    if (!activeReportId) return;
    setDraft({ reportId: activeReportId, modelId: null });
    setActiveChatId(null);
    setQuery('');
    setOpenMenu(null);
  };

  const submitOnEnter = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Shift+Enter remains available for multi-line questions. Ignore IME
    // composition so Enter does not send while a character is being chosen.
    if (event.key !== 'Enter' || event.shiftKey || event.nativeEvent.isComposing) return;
    event.preventDefault();
    formRef.current?.requestSubmit();
  };

  const content = activeReportId ? reportContent[activeReportId] : '';
  const activity = run ? runActivity[run.id] : undefined;
  const running = run && !['completed', 'failed', 'cancelled'].includes(run.status);

  useEffect(() => {
    if (!running) return;
    setActiveRunId(run.id);
    setView('run');
  }, [run?.id, running, setActiveRunId, setView]);

  // Never paint the legacy report workspace for an in-flight run. The effect
  // above hands it to the live run surface on the next client commit.
  if (running) return null;

  const chatOpen = isMobile ? mobileReportChatOpen : !chatCollapsed;

  return <div style={{ flex: 1, minHeight: 0, display: 'flex', position: 'relative' }}>
    <section style={{ flex: 1, minWidth: 0, overflowY: 'auto', padding: isMobile ? '84px 20px 48px' : '100px min(8vw, 96px) 48px' }}>
      <article style={{ maxWidth: '820px', margin: '0 auto' }}>
        <div className="sg-mono" style={{ fontSize: '10.5px', letterSpacing: '.16em', textTransform: 'uppercase', color: 'var(--accent-2)', marginBottom: '14px' }}>Research report</div>
        <h1 style={{ margin: '0 0 14px', fontSize: 'clamp(24px,7vw,36px)', fontWeight: 400, fontStyle: 'italic' }}>{report?.title || 'Research report'}</h1>
        {running && <div style={{ margin: '20px 0', padding: '15px 17px', border: '1px solid var(--border-strong)', borderRadius: '12px', background: 'var(--surface)' }}>
          <div className="sg-mono" style={{ fontSize: '10px', letterSpacing: '.1em', color: 'var(--accent-2)', textTransform: 'uppercase' }}>{activity?.phase || run.status}</div>
          <div style={{ marginTop: '6px', color: 'var(--text-dim)' }}>{activity?.message || 'Research is working…'}</div>
          <button onClick={() => void cancelResearch(run.id).catch(() => undefined)} style={{ marginTop: '12px', padding: '6px 10px', border: '1px solid var(--border)', background: 'transparent', borderRadius: '7px', cursor: 'pointer', color: 'var(--text-dim)' }}>Cancel research</button>
        </div>}
        {run?.status === 'failed' && <div style={{ margin: '20px 0', color: 'var(--color-danger)' }}>{activity?.error || run.error_message || 'Research failed.'}</div>}
        {content ? <div className="chat-message-content report-content" style={{ fontSize: '17px', lineHeight: 1.72 }}><Markdown>{content}</Markdown></div> : !running && <p style={{ color: 'var(--text-dim)' }}>This report has no completed version yet.</p>}
      </article>
    </section>

    {isMobile && !mobileReportChatOpen && (
      <button
        onClick={() => setMobileReportChatOpen(true)}
        title="Open report chat"
        aria-label="Open report chat"
        style={{ position: 'absolute', bottom: '20px', right: '20px', zIndex: 20, width: '52px', height: '52px', borderRadius: '50%', border: 'none', background: 'var(--accent)', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: 'var(--shadow)', cursor: 'pointer' }}
      >
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /></svg>
      </button>
    )}

    <aside
      style={isMobile ? {
        position: 'fixed', inset: 0, zIndex: 70, background: 'var(--surface)',
        display: chatOpen ? 'flex' : 'none', flexDirection: 'column', minHeight: 0,
      } : {
        width: chatCollapsed ? '56px' : '390px', flexShrink: 0, borderLeft: '1px solid var(--border)', background: 'var(--surface)', display: 'flex', flexDirection: 'column', minHeight: 0, transition: 'width 0.3s ease', overflow: 'hidden', position: 'relative',
      }}
    >
      {/* Closed State Button */}
      {!isMobile && (
        <div style={{ position: 'absolute', top: '20px', left: '0', width: '56px', display: 'flex', justifyContent: 'center', transition: 'opacity 0.2s ease', opacity: chatCollapsed ? 1 : 0, pointerEvents: chatCollapsed ? 'auto' : 'none', zIndex: 10 }}>
          <button onClick={toggleChatCollapsed} title="Open chat" style={{ width: '32px', height: '32px', border: '1px solid var(--border)', background: 'var(--surface-2)', borderRadius: '8px', cursor: 'pointer', color: 'var(--text-dim)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            ‹
          </button>
        </div>
      )}

      {/* Open State Content */}
      <div style={{ display: 'flex', flexDirection: 'column', height: '100%', minWidth: isMobile ? undefined : '390px', transition: isMobile ? undefined : 'opacity 0.2s ease', opacity: chatOpen ? 1 : 0, pointerEvents: chatOpen ? 'auto' : 'none' }}>
        <div style={{ padding: '20px 18px 12px', borderBottom: '1px solid var(--border)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
            <div className="sg-mono" style={{ fontSize: '10px', letterSpacing: '.12em', textTransform: 'uppercase', color: 'var(--text-faint)' }}>Report chat</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <button onClick={handleNewChat} title="New report chat" style={{ display: 'flex', alignItems: 'center', gap: '5px', height: '28px', padding: '0 10px', border: '1px solid var(--border)', background: draftChat ? 'var(--accent-soft)' : 'var(--surface-2)', borderRadius: '999px', cursor: 'pointer', color: 'var(--text-dim)', fontSize: '11.5px' }}>
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>
                New
              </button>
              <button onClick={() => (isMobile ? setMobileReportChatOpen(false) : toggleChatCollapsed())} title="Close chat" style={{ width: '28px', height: '28px', border: '1px solid var(--border)', background: 'transparent', borderRadius: '6px', cursor: 'pointer', color: 'var(--text-dim)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                {isMobile ? '✕' : '›'}
              </button>
            </div>
          </div>
          {(reportChats.length > 1 || draftChat) && <div style={{ position: 'relative' }}>
            <button type="button" onClick={() => setOpenMenu(openMenu === 'thread' ? null : 'thread')} style={{ display: 'flex', alignItems: 'center', gap: '7px', width: '100%', height: '32px', padding: '0 9px', border: '1px solid var(--border)', borderRadius: '8px', background: 'var(--surface-2)', color: 'var(--text-dim)', cursor: 'pointer', fontSize: '12px', textAlign: 'left' }}><span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{draftChat ? `New chat · ${draftModelLabel}` : selectedChat?.title || 'Untitled chat'}</span><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="6 9 12 15 18 9" /></svg></button>
            {openMenu === 'thread' && <div className="animate-sg-pop" style={{ position: 'absolute', top: 'calc(100% + 6px)', zIndex: 25, width: '100%', maxHeight: '220px', overflowY: 'auto', padding: '5px', border: '1px solid var(--border-strong)', borderRadius: '10px', background: 'var(--surface)', boxShadow: 'var(--shadow)' }}>
              {draftChat && <button type="button" onClick={() => setOpenMenu(null)} style={{ display: 'block', width: '100%', padding: '8px', border: 'none', borderRadius: '7px', background: 'var(--accent-soft)', color: 'var(--text)', cursor: 'pointer', textAlign: 'left', fontSize: '12px' }}>New chat · {draftModelLabel}</button>}
              {reportChats.map((chat) => <button key={chat.id} type="button" onClick={() => { setDraft(null); setActiveChatId(chat.id); setOpenMenu(null); }} style={{ display: 'block', width: '100%', padding: '8px', border: 'none', borderRadius: '7px', background: chat.id === selectedChat?.id ? 'var(--accent-soft)' : 'transparent', color: 'var(--text)', cursor: 'pointer', textAlign: 'left', fontSize: '12px' }}>{chat.title || 'Untitled chat'}</button>)}
            </div>}
          </div>}
        </div>
        <div ref={chatScrollRef} style={{ flex: 1, minHeight: 0, overflowY: 'auto', padding: '18px', display: 'flex', flexDirection: 'column', gap: '18px' }}>
          {!turns.length && <p style={{ color: 'var(--text-faint)', fontSize: '14px' }}>{draftChat ? `New report chat using ${draftModelLabel}. Send your first message to create it.` : 'Ask about this finalized report. The backend retrieves relevant report passages for each answer.'}</p>}
          {turns.map((message) => <div key={message.id} style={{ alignSelf: message.role === 'user' ? 'flex-end' : 'flex-start', maxWidth: '88%' }}><div className="sg-mono" style={{ fontSize: '9px', color: 'var(--text-faint)', marginBottom: '5px' }}>{message.role === 'user' ? 'YOU' : 'SINGULARITY'}</div>{message.pending ? <div className="sg-thinking" aria-label="Singularity is thinking"><span /><span /><span /></div> : <div className="chat-message-content" style={{ lineHeight: 1.5, padding: message.role === 'user' ? '10px 12px' : 0, borderRadius: '12px', background: message.role === 'user' ? 'var(--surface-3)' : 'transparent' }}>{message.content ? <Markdown>{message.content}</Markdown> : '…'}</div>}</div>)}
        </div>
        <form ref={formRef} onSubmit={submit} style={{ padding: '14px', borderTop: '1px solid var(--border)' }}>
          <textarea value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={submitOnEnter} placeholder="Ask a follow-up about this report…" rows={2} style={{ width: '100%', resize: 'none', padding: '10px', border: '1px solid var(--border-strong)', borderRadius: '10px', background: 'var(--surface-2)', color: 'var(--text)' }} />
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '8px' }}>
            <div style={{ position: 'relative', minWidth: 0, flex: 1 }}>
              <button type="button" onClick={() => setOpenMenu(openMenu === 'model' ? null : 'model')} style={{ display: 'flex', alignItems: 'center', gap: '6px', width: '100%', height: '32px', padding: '0 9px', border: '1px solid var(--border)', borderRadius: '8px', background: 'var(--surface-2)', color: 'var(--text-dim)', cursor: 'pointer', fontFamily: 'var(--font-mono)', fontSize: '11px', textAlign: 'left' }}><span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{draftChat ? draftModelLabel : 'Model locked for this chat'}</span><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="6 9 12 15 18 9" /></svg></button>
              {openMenu === 'model' && <div className="animate-sg-pop" style={{ position: 'absolute', bottom: 'calc(100% + 8px)', left: 0, zIndex: 30, width: '250px', maxHeight: '260px', overflowY: 'auto', padding: '6px', border: '1px solid var(--border-strong)', borderRadius: '12px', background: 'var(--surface)', boxShadow: 'var(--shadow)' }}>
                <div className="sg-mono" style={{ padding: '5px 7px 7px', fontSize: '9.5px', letterSpacing: '.11em', color: 'var(--text-faint)', textTransform: 'uppercase' }}>{draftChat ? 'Model for this new chat' : 'Start a new chat to change model'}</div>
                {draftChat && (modelsLoading ? <div className="sg-mono" style={{ padding: '10px 7px', fontSize: '11px', color: 'var(--text-faint)' }}>Loading your provider&apos;s models…</div> : availableModels.length ? availableModels.map((model) => <button key={model.id} type="button" onClick={() => { setDraft((current) => current && current.reportId === activeReportId ? { ...current, modelId: model.id } : current); setOpenMenu(null); }} style={{ display: 'flex', alignItems: 'center', width: '100%', padding: '9px 8px', border: 'none', borderRadius: '8px', background: model.id === effectiveDraftModelId ? 'var(--accent-soft)' : 'transparent', color: 'var(--text)', cursor: 'pointer', fontFamily: 'var(--font-mono)', fontSize: '11.5px', textAlign: 'left' }}><span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{model.id}</span></button>) : <div className="sg-mono" style={{ padding: '10px 7px', fontSize: '11px', lineHeight: 1.45, color: 'var(--text-faint)' }}>Add a model provider in Settings first.</div>) }
              </div>}
            </div>
            <button type="submit" disabled={!query.trim() || sending} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: '90px', height: '32px', border: 'none', borderRadius: '8px', background: 'var(--accent)', color: '#fff', cursor: sending ? 'default' : 'pointer', fontSize: '12.5px', opacity: !query.trim() || sending ? 0.6 : 1 }}>{sending ? 'Sending…' : 'Send'}</button>
          </div>
        </form>
      </div>
    </aside>
  </div>;
}

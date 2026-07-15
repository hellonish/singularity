'use client';

import { useEffect, useState } from 'react';
import { Intensity, useAppStore } from '@/store/app-store';
import { INTENSITIES, PROVIDERS } from '@/lib/dummy-data';
import { useWorkspace } from '@/components/workspace-provider';

export function Composer() {
  const { mode, intensity, modelId, view, activeChatId, openMenu, researchApprovalMode, setResearchApprovalMode, setOpenMenu, setMode, setIntensity, setModelId, composerDraft, setActiveChatId, setActiveReportId, setActiveRunId, setActivePreparationId, setView, setComposerDraft, setSettingsOpen, setActiveSettingsTab } = useAppStore();
  const { createAndSendChat, sendChat, prepareResearch, activeCredential, availableModels, modelsLoading, setDefaultModel, clearError, streamingChatIds } = useWorkspace();
  const [query, setQuery] = useState('');
  const [sending, setSending] = useState(false);
  // Switching to Research abandons the open chat, so confirm first when one is active.
  const [researchConfirmOpen, setResearchConfirmOpen] = useState(false);

  // Research always runs in a fresh chat. From the home/grid there is nothing to
  // lose, so switch silently; inside an open chat, confirm before discarding it.
  const selectResearchMode = () => {
    setOpenMenu(null);
    if (view === 'chat' && activeChatId) {
      setResearchConfirmOpen(true);
    } else {
      setMode('research');
    }
  };

  const confirmResearchMode = () => {
    setResearchConfirmOpen(false);
    setMode('research');
    // Start a new chat: drop the active conversation and return to the home view.
    setActiveChatId(null);
    setView('grid');
  };

  // Onboarding "types" a starter message by growing composerDraft one character
  // at a time. Mirror it live into the field so the user sees it being typed and
  // it stays in the box for them to send.
  useEffect(() => {
    if (!composerDraft) return;
    const applyDraft = window.setTimeout(() => setQuery(composerDraft), 0);
    return () => window.clearTimeout(applyDraft);
  }, [composerDraft]);

  const modeLabel = mode === 'research' ? 'Research' : 'Chat';
  const intensityName = INTENSITIES.find(i => i.id === intensity)?.name || 'Medium';
  // Both chat and research depend on the provider honoring response_format
  // (structured outputs), so only ever offer models whose live catalog
  // advertises it.
  const selectableModels = availableModels.filter((model) => model.supports_research);
  const effectiveModelId = selectableModels.some((model) => model.id === modelId)
    ? modelId
    : selectableModels.find((model) => model.id === activeCredential?.default_model_id)?.id
      ?? selectableModels[0]?.id
      ?? '';
  const selectedModel = selectableModels.find((model) => model.id === effectiveModelId);
  const modelName = modelsLoading ? 'Loading models…' : selectedModel?.id || (mode === 'research' ? 'Select research model' : 'Select model');
  const modelDot = activeCredential
    ? PROVIDERS.find((provider) => provider.id === activeCredential.provider)?.dot || 'var(--text-faint)'
    : 'var(--text-faint)';

  const toggleMenu = (menu: 'mode' | 'approval' | 'effort' | 'model') => {
    setOpenMenu(openMenu === menu ? null : menu);
  };

  // While the open chat is answering, hold new sends so turns can't interleave.
  const chatBusy = mode === 'chat' && view === 'chat' && !!activeChatId && streamingChatIds.includes(activeChatId);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const content = query.trim();
    if (!content || sending || chatBusy || (mode === 'research' && content.length < 10)) return;
    clearError();
    setSending(true);
    try {
      if (mode === 'chat') {
        // Inside an open chat the composer continues that conversation; a new
        // chat is created only from the home/grid view.
        if (view === 'chat' && activeChatId) {
          void sendChat(activeChatId, content, intensity);
        } else {
          const chat = await createAndSendChat(content, undefined, selectedModel?.id, intensity);
          setActiveChatId(chat.id);
          setView('chat');
        }
      } else {
        const strength = intensity === 'instant' ? 1 : intensity === 'medium' ? 2 : 3;
        const result = await prepareResearch(content, strength, researchApprovalMode, selectedModel?.id);
        setActivePreparationId(result.preparation.id);
        if (result.run) {
          setActiveRunId(result.run.id);
          if (result.run.report_id) setActiveReportId(result.run.report_id);
          setView('run');
        } else {
          setView('prepare');
        }
      }
      setQuery('');
      setComposerDraft('');
      setOpenMenu(null);
    } catch {
      // Workspace state opens the human-readable error modal.
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      void handleSubmit(e as unknown as React.FormEvent);
    }
  };

  const canSend = query.trim().length > 0 && !sending && !chatBusy && !!activeCredential && !!selectedModel && !(mode === 'research' && query.trim().length < 10);
  const hintLine = mode === 'research'
    ? (query.trim().length > 0 && query.trim().length < 10 ? 'Keep typing to start a deep research run (min 10 chars).' : 'Shift + Enter for new line')
    : chatBusy ? 'Singularity is replying…' : 'Shift + Enter for new line';

  return (
    <div style={{ flexShrink: 0, padding: '14px 24px 22px', background: 'linear-gradient(0deg, var(--bg) 62%, transparent)' }}>
      <form
        data-tour="composer"
        onSubmit={handleSubmit}
        style={{ maxWidth: '900px', margin: '0 auto', backgroundColor: 'var(--surface)', border: '1px solid var(--border-strong)', borderRadius: '20px', boxShadow: 'var(--shadow)', position: 'relative' }}
      >
        <div style={{ display: 'flex', alignItems: 'flex-end', gap: '8px', padding: '14px 14px 6px' }}>
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
            placeholder={mode === 'research' ? 'What do you want to research?' : 'Message Singularity...'}
            style={{ flex: 1, resize: 'none', border: 'none', outline: 'none', background: 'transparent', color: 'var(--text)', fontFamily: 'var(--font-serif)', fontSize: '18px', lineHeight: 1.5, maxHeight: '150px', padding: '4px 4px' }}
          />
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 12px 12px' }}>
          
          {/* Mode Chip */}
          <div style={{ position: 'relative' }}>
            <button
              data-tour="mode"
              type="button"
              onClick={() => toggleMenu('mode')}
              style={{ display: 'flex', alignItems: 'center', gap: '7px', height: '32px', padding: '0 11px', border: '1px solid var(--border)', backgroundColor: 'var(--surface-2)', borderRadius: '10px', cursor: 'pointer', color: 'var(--text)', fontFamily: 'var(--font-mono)', fontSize: '12px' }}
            >
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', border: '2px solid', borderColor: mode === 'research' ? 'var(--text-dim)' : 'transparent', backgroundColor: mode === 'research' ? 'transparent' : 'var(--text-dim)' }}></span>
              {modeLabel}
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ opacity: 0.5 }}><polyline points="6 9 12 15 18 9" /></svg>
            </button>
            {openMenu === 'mode' && (
              <div className="animate-sg-pop" style={{ position: 'absolute', bottom: 'calc(100% + 8px)', left: 0, width: '236px', backgroundColor: 'var(--surface)', border: '1px solid var(--border-strong)', borderRadius: '14px', boxShadow: 'var(--shadow)', padding: '8px', zIndex: 50 }}>
                <div className="sg-mono" style={{ fontSize: '9.5px', letterSpacing: '.13em', textTransform: 'uppercase', color: 'var(--text-faint)', padding: '3px 6px 7px' }}>Mode</div>
                <button type="button" onClick={() => { setMode('chat'); setOpenMenu(null); }} style={{ display: 'flex', alignItems: 'center', gap: '11px', width: '100%', padding: '9px 10px', borderRadius: '10px', cursor: 'pointer', border: '1px solid transparent', backgroundColor: mode === 'chat' ? 'var(--accent-soft)' : 'transparent', color: 'var(--text)' }}>
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" style={{ flexShrink: 0 }}><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /></svg>
                  <span style={{ flex: 1, textAlign: 'left', fontSize: '14px', fontWeight: 500 }}>Chat</span>
                  {mode === 'chat' && <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--accent-2)" strokeWidth="2.4"><polyline points="20 6 9 17 4 12" /></svg>}
                </button>
                <button type="button" onClick={selectResearchMode} style={{ display: 'flex', alignItems: 'center', gap: '11px', width: '100%', padding: '9px 10px', borderRadius: '10px', cursor: 'pointer', border: '1px solid transparent', backgroundColor: mode === 'research' ? 'var(--accent-soft)' : 'transparent', color: 'var(--text)' }}>
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" style={{ flexShrink: 0 }}><circle cx="11" cy="11" r="7" /><line x1="21" y1="21" x2="16.65" y2="16.65" /></svg>
                  <span style={{ flex: 1, textAlign: 'left', fontSize: '14px', fontWeight: 500 }}>Research</span>
                  {mode === 'research' && <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--accent-2)" strokeWidth="2.4"><polyline points="20 6 9 17 4 12" /></svg>}
                </button>
              </div>
            )}
          </div>

          {mode === 'research' && (
            <div style={{ position: 'relative' }}>
              <button
                type="button"
                onClick={() => toggleMenu('approval')}
                style={{ display: 'flex', alignItems: 'center', gap: '7px', height: '32px', padding: '0 11px', border: '1px solid var(--border)', backgroundColor: 'var(--surface-2)', borderRadius: '10px', cursor: 'pointer', color: 'var(--text)', fontFamily: 'var(--font-mono)', fontSize: '12px' }}
              >
                {researchApprovalMode === 'ask' ? 'Ask for approval' : 'Auto mode'}
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ opacity: 0.5 }}><polyline points="6 9 12 15 18 9" /></svg>
              </button>
              {openMenu === 'approval' && (
                <div className="animate-sg-pop" style={{ position: 'absolute', bottom: 'calc(100% + 8px)', left: 0, width: '260px', backgroundColor: 'var(--surface)', border: '1px solid var(--border-strong)', borderRadius: '14px', boxShadow: 'var(--shadow)', padding: '8px', zIndex: 50 }}>
                  {([
                    ['ask', 'Ask for approval', 'Show the plan and ask only essential questions before searching.'],
                    ['auto', 'Auto mode', 'Resolve the likely entity and begin research immediately.'],
                  ] as const).map(([id, label, description]) => (
                    <button key={id} type="button" onClick={() => { setResearchApprovalMode(id); setOpenMenu(null); }} style={{ display: 'block', width: '100%', padding: '10px', border: 'none', borderRadius: '10px', textAlign: 'left', cursor: 'pointer', color: 'var(--text)', background: researchApprovalMode === id ? 'var(--accent-soft)' : 'transparent' }}>
                      <span style={{ display: 'block', fontSize: '13.5px', fontWeight: 600 }}>{label}</span>
                      <span style={{ display: 'block', marginTop: '3px', fontSize: '11.5px', lineHeight: 1.4, color: 'var(--text-dim)' }}>{description}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Effort Chip */}
          <div style={{ position: 'relative' }}>
            <button
              type="button"
              onClick={() => toggleMenu('effort')}
              style={{ display: 'flex', alignItems: 'center', gap: '7px', height: '32px', padding: '0 11px', border: '1px solid var(--border)', backgroundColor: 'var(--surface-2)', borderRadius: '10px', cursor: 'pointer', color: 'var(--text)', fontFamily: 'var(--font-mono)', fontSize: '12px' }}
            >
              {intensityName}
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ opacity: 0.5 }}><polyline points="6 9 12 15 18 9" /></svg>
            </button>
            {openMenu === 'effort' && (
              <div className="animate-sg-pop" style={{ position: 'absolute', bottom: 'calc(100% + 8px)', left: 0, width: '200px', backgroundColor: 'var(--surface)', border: '1px solid var(--border-strong)', borderRadius: '14px', boxShadow: 'var(--shadow)', padding: '8px', zIndex: 50 }}>
                <div className="sg-mono" style={{ fontSize: '9.5px', letterSpacing: '.13em', textTransform: 'uppercase', color: 'var(--text-faint)', padding: '3px 6px 7px' }}>Effort</div>
                {INTENSITIES.map((it) => (
                  <button
                    key={it.id}
                    type="button"
                    onClick={() => { setIntensity(it.id as Intensity); setOpenMenu(null); }}
                    style={{ display: 'flex', alignItems: 'center', gap: '11px', width: '100%', padding: '9px 10px', borderRadius: '10px', cursor: 'pointer', border: '1px solid transparent', backgroundColor: intensity === it.id ? 'var(--accent-soft)' : 'transparent', color: 'var(--text)' }}
                  >
                    <span style={{ flex: 1, textAlign: 'left', fontSize: '14.5px', fontWeight: 500 }}>{it.name}</span>
                    {intensity === it.id && <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--accent-2)" strokeWidth="2.4" style={{ flexShrink: 0 }}><polyline points="20 6 9 17 4 12" /></svg>}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Model Chip */}
          <div style={{ position: 'relative' }}>
            <button
              type="button"
              onClick={() => toggleMenu('model')}
              style={{ display: 'flex', alignItems: 'center', gap: '7px', height: '32px', padding: '0 11px', border: '1px solid var(--border)', backgroundColor: 'var(--surface-2)', borderRadius: '10px', cursor: 'pointer', color: 'var(--text)', fontFamily: 'var(--font-mono)', fontSize: '12px' }}
            >
              <span style={{ width: '7px', height: '7px', borderRadius: '50%', backgroundColor: modelDot }}></span>
              {modelName}
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ opacity: 0.5 }}><polyline points="6 9 12 15 18 9" /></svg>
            </button>
            {openMenu === 'model' && (
              <div className="animate-sg-pop" style={{ position: 'absolute', bottom: 'calc(100% + 8px)', left: 0, width: '250px', maxHeight: '300px', overflowY: 'auto', backgroundColor: 'var(--surface)', border: '1px solid var(--border-strong)', borderRadius: '13px', boxShadow: 'var(--shadow)', padding: '6px', zIndex: 50 }}>
                {modelsLoading ? (
                  <div className="sg-mono" style={{ padding: '12px 9px', fontSize: '11px', color: 'var(--text-faint)' }}>Loading your provider&apos;s models…</div>
                ) : selectableModels.length ? selectableModels.map((model) => (
                  <button
                    key={model.id}
                    type="button"
                    onClick={() => {
                      setModelId(model.id); setOpenMenu(null);
                      void setDefaultModel(model.id).catch(() => undefined);
                    }}
                    style={{ display: 'flex', alignItems: 'center', gap: '8px', width: '100%', padding: '8px 9px', border: 'none', borderRadius: '8px', cursor: 'pointer', fontFamily: 'var(--font-mono)', fontSize: '12.5px', backgroundColor: effectiveModelId === model.id ? 'var(--accent-soft)' : 'transparent', color: 'var(--text)' }}
                  >
                    <span style={{ flex: 1, minWidth: 0, textAlign: 'left', overflow: 'hidden', textOverflow: 'ellipsis' }}>{model.id}</span>
                    {effectiveModelId === model.id && <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--accent-2)" strokeWidth="2.4"><polyline points="20 6 9 17 4 12" /></svg>}
                  </button>
                )) : mode === 'research' && availableModels.length ? (
                  <div className="sg-mono" style={{ padding: '12px 9px', fontSize: '11px', lineHeight: 1.5, color: 'var(--text-faint)' }}>
                    This provider has no models that support Research&apos;s JSON workflow.
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={() => {
                      setSettingsOpen(true);
                      setActiveSettingsTab('models');
                      setOpenMenu(null);
                    }}
                    className="sg-mono"
                    style={{ display: 'block', width: '100%', textAlign: 'left', padding: '12px 9px', fontSize: '11px', color: 'var(--text)', cursor: 'pointer', border: 'none', backgroundColor: 'transparent' }}
                  >
                    Add Model Provider in Settings
                  </button>
                )}
              </div>
            )}
          </div>

          <button
            type="submit"
            title="Send"
            disabled={!canSend}
            style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', marginLeft: 'auto', width: '32px', height: '32px', borderRadius: '10px', border: 'none', backgroundColor: canSend ? 'var(--accent)' : 'var(--surface-3)', color: canSend ? '#fff' : 'var(--text-faint)', cursor: canSend ? 'pointer' : 'default', transition: 'background-color 0.2s, color 0.2s' }}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="12" y1="19" x2="12" y2="5" /><polyline points="5 12 12 5 19 12" /></svg>
          </button>
        </div>
        {openMenu && <div onClick={() => setOpenMenu(null)} style={{ position: 'fixed', inset: 0, zIndex: 40 }}></div>}
      </form>
      <div className="sg-mono" style={{ maxWidth: '900px', margin: '9px auto 0', fontSize: '10.5px', color: 'var(--text-faint)', textAlign: 'center' }}>
        {!activeCredential ? 'Add a provider key in Settings to send messages.' : hintLine}
      </div>

      {researchConfirmOpen && (
        <div
          role="dialog"
          aria-modal="true"
          onClick={() => setResearchConfirmOpen(false)}
          style={{ position: 'fixed', inset: 0, zIndex: 60, backgroundColor: 'rgba(6,9,14,0.58)', backdropFilter: 'blur(3px)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '24px' }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{ width: '100%', maxWidth: '400px', backgroundColor: 'var(--surface)', border: '1px solid var(--border-strong)', borderRadius: '18px', boxShadow: 'var(--shadow)', padding: '22px' }}
          >
            <div style={{ fontFamily: 'var(--font-serif)', fontSize: '18px', fontWeight: 500, color: 'var(--text)' }}>Start a new chat?</div>
            <div style={{ marginTop: '9px', fontSize: '14px', lineHeight: 1.5, color: 'var(--text-dim)' }}>Research requires a new chat.</div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '9px', marginTop: '22px' }}>
              <button
                type="button"
                onClick={() => setResearchConfirmOpen(false)}
                style={{ height: '36px', padding: '0 15px', borderRadius: '10px', border: '1px solid var(--border-strong)', backgroundColor: 'var(--surface-2)', color: 'var(--text)', cursor: 'pointer', fontSize: '13.5px' }}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={confirmResearchMode}
                style={{ height: '36px', padding: '0 15px', borderRadius: '10px', border: 'none', backgroundColor: 'var(--accent)', color: '#fff', cursor: 'pointer', fontSize: '13.5px' }}
              >
                Continue
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

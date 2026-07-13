'use client';

import { useEffect, useState } from 'react';
import { useAppStore } from '@/store/app-store';
import { INTENSITIES, MODELS } from '@/lib/dummy-data';

export function Composer() {
  const { mode, intensity, modelId, openMenu, setOpenMenu, setMode, setIntensity, setModelId, composerDraft } = useAppStore();
  const [query, setQuery] = useState('');

  // Onboarding "types" a starter message by growing composerDraft one character
  // at a time. Mirror it live into the field so the user sees it being typed and
  // it stays in the box for them to send.
  useEffect(() => {
    if (composerDraft) setQuery(composerDraft);
  }, [composerDraft]);

  const modeLabel = mode === 'research' ? 'Research' : 'Chat';
  const intensityName = INTENSITIES.find(i => i.id === intensity)?.name || 'Medium';
  const selectedModel = MODELS.flatMap(g => g.items).find(m => m.id === modelId);
  const modelName = selectedModel?.name || 'Select model';
  const modelGroup = MODELS.find(g => g.items.some(m => m.id === modelId));
  const modelDot = modelGroup?.dot || 'var(--text-faint)';

  const toggleMenu = (menu: 'mode' | 'effort' | 'model') => {
    setOpenMenu(openMenu === menu ? null : menu);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    if (mode === 'research' && query.trim().length < 10) return;
    
    // In a real app, this would send a message
    console.log('Sending message:', query);
    setQuery('');
    setOpenMenu(null);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as unknown as React.FormEvent);
    }
  };

  const canSend = query.trim().length > 0 && !(mode === 'research' && query.trim().length < 10);
  const hintLine = mode === 'research' 
    ? (query.trim().length > 0 && query.trim().length < 10 ? 'Keep typing to start a deep research run (min 10 chars).' : 'Shift + Enter for new line')
    : 'Shift + Enter for new line';

  return (
    <div style={{ flexShrink: 0, padding: '14px 24px 22px', background: 'linear-gradient(0deg, var(--bg) 62%, transparent)' }}>
      <form
        data-tour="composer"
        onSubmit={handleSubmit}
        style={{ maxWidth: '720px', margin: '0 auto', backgroundColor: 'var(--surface)', border: '1px solid var(--border-strong)', borderRadius: '20px', boxShadow: 'var(--shadow)', position: 'relative' }}
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
                <button type="button" onClick={() => { setMode('research'); setOpenMenu(null); }} style={{ display: 'flex', alignItems: 'center', gap: '11px', width: '100%', padding: '9px 10px', borderRadius: '10px', cursor: 'pointer', border: '1px solid transparent', backgroundColor: mode === 'research' ? 'var(--accent-soft)' : 'transparent', color: 'var(--text)' }}>
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" style={{ flexShrink: 0 }}><circle cx="11" cy="11" r="7" /><line x1="21" y1="21" x2="16.65" y2="16.65" /></svg>
                  <span style={{ flex: 1, textAlign: 'left', fontSize: '14px', fontWeight: 500 }}>Research</span>
                  {mode === 'research' && <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--accent-2)" strokeWidth="2.4"><polyline points="20 6 9 17 4 12" /></svg>}
                </button>
              </div>
            )}
          </div>

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
                    onClick={() => { setIntensity(it.id as any); setOpenMenu(null); }}
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
                        onClick={() => { setModelId(mi.id); setOpenMenu(null); }}
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
            disabled={!canSend}
            style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', marginLeft: 'auto', width: '32px', height: '32px', borderRadius: '10px', border: 'none', backgroundColor: canSend ? 'var(--accent)' : 'var(--surface-3)', color: canSend ? '#fff' : 'var(--text-faint)', cursor: canSend ? 'pointer' : 'default', transition: 'background-color 0.2s, color 0.2s' }}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="12" y1="19" x2="12" y2="5" /><polyline points="5 12 12 5 19 12" /></svg>
          </button>
        </div>
        {openMenu && <div onClick={() => setOpenMenu(null)} style={{ position: 'fixed', inset: 0, zIndex: 40 }}></div>}
      </form>
      <div className="sg-mono" style={{ maxWidth: '720px', margin: '9px auto 0', fontSize: '10.5px', color: 'var(--text-faint)', textAlign: 'center' }}>
        {hintLine}
      </div>
    </div>
  );
}

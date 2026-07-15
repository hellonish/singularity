'use client';

import { useState } from 'react';
import { useAppStore, ACCENT_COLORS, Theme } from '@/store/app-store';
import { PROVIDERS } from '@/lib/dummy-data';
import { useWorkspace } from '@/components/workspace-provider';
import { ProviderCredential } from '@/lib/api';

type Provider = (typeof PROVIDERS)[number];

function ProviderLogo({ p, size = 20 }: { p: Provider; size?: number }) {
  // The logos are monochrome SVGs. An external SVG loaded via <img> can't be
  // recolored by CSS, so we use it as a mask and paint it with the theme text
  // color — black in light mode, white in dark mode.
  return (
    <span
      role="img"
      aria-label={p.name}
      style={{
        display: 'inline-block', width: size, height: size, flexShrink: 0,
        backgroundColor: 'var(--text)',
        WebkitMaskImage: `url(${p.logo})`,
        maskImage: `url(${p.logo})`,
        WebkitMaskRepeat: 'no-repeat',
        maskRepeat: 'no-repeat',
        WebkitMaskPosition: 'center',
        maskPosition: 'center',
        WebkitMaskSize: 'contain',
        maskSize: 'contain',
      }}
    />
  );
}

// Custom provider picker: a dropdown listing every provider with its logo + name.
// Selecting one opens that provider's setup panel below.
function ProviderDropdown({
  value, connectedIds, onSelect, forceOpen, highlight,
}: {
  value: string | null;
  connectedIds: Set<string>;
  onSelect: (id: string) => void;
  forceOpen?: boolean;         // onboarding can force the menu open
  highlight?: string | null;   // onboarding can pre-highlight an option (hover-style)
}) {
  const [localOpen, setLocalOpen] = useState(false);
  const open = localOpen || !!forceOpen;
  const setOpen = setLocalOpen;
  const selected = PROVIDERS.find((p) => p.id === value) || null;

  return (
    <div data-tour="providers" style={{ position: 'relative' }}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        style={{
          display: 'flex', alignItems: 'center', gap: '11px', width: '100%', height: '52px',
          padding: '0 14px', textAlign: 'left', cursor: 'pointer',
          borderRadius: '13px',
          border: open ? '1px solid var(--accent)' : '1px solid var(--border-strong)',
          backgroundColor: 'var(--surface-2)', color: 'var(--text)',
          transition: 'border-color .15s',
        }}
      >
        {selected ? (
          <>
            <ProviderLogo p={selected} />
            <span style={{ display: 'flex', flexDirection: 'column', minWidth: 0, flex: 1 }}>
              <span style={{ fontSize: '15px', fontWeight: 500 }}>{selected.name}</span>
              <span className="sg-mono" style={{ fontSize: '11px', color: 'var(--text-faint)' }}>{selected.sub}</span>
            </span>
            {connectedIds.has(selected.id) && (
              <span className="sg-mono" style={{ padding: '2px 8px', borderRadius: '999px', fontSize: '9.5px', letterSpacing: '.05em', backgroundColor: 'rgba(63,200,164,0.1)', color: 'var(--ok)' }}>Connected</span>
            )}
          </>
        ) : (
          <span style={{ flex: 1, fontSize: '14.5px', color: 'var(--text-faint)' }}>Choose a provider…</span>
        )}
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ opacity: 0.5, flexShrink: 0, transform: open ? 'rotate(180deg)' : 'none', transition: 'transform .18s' }}><polyline points="6 9 12 15 18 9" /></svg>
      </button>

      {open && (
        <>
          {/* z above the onboarding overlay (which sits at 64–68) so the menu
              stays interactive while the tour is highlighting this dropdown. */}
          <div onClick={() => setOpen(false)} style={{ position: 'fixed', inset: 0, zIndex: 70 }} />
          <div
            data-tour-popover
            className="animate-sg-pop"
            style={{
              position: 'absolute', top: 'calc(100% + 6px)', left: 0, right: 0, zIndex: 71,
              backgroundColor: 'var(--surface)', border: '1px solid var(--border-strong)',
              borderRadius: '13px', boxShadow: 'var(--shadow)', padding: '6px', maxHeight: '288px', overflowY: 'auto',
            }}
          >
            {PROVIDERS.map((p) => {
              const active = p.id === value;
              const highlighted = p.id === highlight;
              return (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => { onSelect(p.id); setOpen(false); }}
                  style={{
                    display: 'flex', alignItems: 'center', gap: '11px', width: '100%', padding: '9px 10px',
                    borderRadius: '10px', cursor: 'pointer', textAlign: 'left', color: 'var(--text)',
                    border: highlighted ? '1px solid var(--accent)' : '1px solid transparent',
                    backgroundColor: highlighted ? 'var(--accent-soft)' : active ? 'var(--accent-soft)' : 'transparent',
                    transition: 'background-color .15s, border-color .15s',
                  }}
                >
                  <ProviderLogo p={p} />
                  <span style={{ display: 'flex', flexDirection: 'column', minWidth: 0, flex: 1 }}>
                    <span style={{ fontSize: '14px', fontWeight: 500 }}>{p.name}</span>
                    <span className="sg-mono" style={{ fontSize: '10.5px', color: 'var(--text-faint)' }}>{p.sub}</span>
                  </span>
                  {connectedIds.has(p.id) && (
                    <span style={{ width: '7px', height: '7px', borderRadius: '50%', backgroundColor: 'var(--ok)', flexShrink: 0 }} />
                  )}
                  {active && (
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--accent-2)" strokeWidth="2.4" style={{ flexShrink: 0 }}><polyline points="20 6 9 17 4 12" /></svg>
                  )}
                </button>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}

export function SettingsModal() {
  const { settingsOpen, setSettingsOpen, openProvider, setOpenProvider, theme, setTheme, accent, setAccent, activeSettingsTab, setActiveSettingsTab, obAdvance, forceProviderMenuOpen, providerHighlight } = useAppStore();
  const [currentKeys, setCurrentKeys] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const { credentials, activeCredential, selectCredential, saveCredential, disableCredential, clearError } = useWorkspace();

  if (!settingsOpen) return null;

  const detail = PROVIDERS.find((p) => p.id === openProvider) || null;
  const detailCredential = detail
    ? credentials.find((credential) => credential.provider === detail.id && credential.status === 'active')
    : null;

  return (
    <div
      onClick={() => setSettingsOpen(false)}
      className="animate-sg-scrim"
      style={{ position: 'fixed', inset: 0, zIndex: 60, backgroundColor: 'rgba(6,9,14,0.58)', backdropFilter: 'blur(3px)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '24px' }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        data-screen-label="Settings"
        className="animate-sg-pop"
        style={{ width: 'min(760px, 100%)', height: '86vh', display: 'flex', flexDirection: 'column', backgroundColor: 'var(--surface)', border: '1px solid var(--border-strong)', borderRadius: '20px', boxShadow: 'var(--shadow)', overflow: 'hidden' }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '20px 24px', borderBottom: '1px solid var(--border)' }}>
          <div>
            <div className="sg-mono" style={{ fontSize: '10px', letterSpacing: '.15em', textTransform: 'uppercase', color: 'var(--text-faint)', marginBottom: '5px' }}>Settings</div>
            <h2 style={{ margin: 0, fontSize: '23px', fontWeight: 400, letterSpacing: '-.01em' }}>{activeSettingsTab === 'models' ? 'Model providers' : 'Appearance'}</h2>
          </div>
          <button
            onClick={() => setSettingsOpen(false)}
            style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', justifyContent: 'center', width: '34px', height: '34px', border: '1px solid var(--border)', backgroundColor: 'var(--surface-2)', color: 'var(--text-dim)', borderRadius: '9px', cursor: 'pointer' }}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
          </button>
        </div>
        <div style={{ display: 'flex', minHeight: 0, flex: 1 }}>
          <div style={{ width: '212px', flexShrink: 0, borderRight: '1px solid var(--border)', padding: '12px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <button
              onClick={() => setActiveSettingsTab('models')}
              style={{ display: 'flex', alignItems: 'center', gap: '10px', width: '100%', padding: '9px 10px', borderRadius: '11px', cursor: 'pointer', transition: 'all .15s', border: '1px solid transparent', color: 'var(--text)', backgroundColor: activeSettingsTab === 'models' ? 'var(--surface-2)' : 'transparent', borderColor: activeSettingsTab === 'models' ? 'var(--border)' : 'transparent' }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--text-dim)" strokeWidth="2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>
              <span style={{ flex: 1, minWidth: 0, textAlign: 'left', fontSize: '14px', fontWeight: 500 }}>Models</span>
            </button>
            <button
              onClick={() => setActiveSettingsTab('appearance')}
              style={{ display: 'flex', alignItems: 'center', gap: '10px', width: '100%', padding: '9px 10px', borderRadius: '11px', cursor: 'pointer', transition: 'all .15s', border: '1px solid transparent', color: 'var(--text)', backgroundColor: activeSettingsTab === 'appearance' ? 'var(--surface-2)' : 'transparent', borderColor: activeSettingsTab === 'appearance' ? 'var(--border)' : 'transparent' }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--text-dim)" strokeWidth="2"><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41M12 7a5 5 0 1 0 0 10 5 5 0 0 0 0-10z"/></svg>
              <span style={{ flex: 1, minWidth: 0, textAlign: 'left', fontSize: '14px', fontWeight: 500 }}>Appearance</span>
            </button>
          </div>
          <div style={{ flex: 1, minWidth: 0, padding: '24px', overflowY: 'auto' }}>
            {activeSettingsTab === 'models' ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', paddingBottom: '8px' }}>
                <p style={{ margin: 0, fontSize: '14.5px', color: 'var(--text-dim)', lineHeight: 1.5 }}>
                  Choose a provider to power your AI, then add its API key. You can connect several — you bring your own keys, and usage bills to your own account.
                </p>

                {/* Provider selector */}
                <ProviderDropdown
                  value={openProvider}
                  connectedIds={new Set(credentials.filter((credential) => credential.status === 'active').map((credential) => credential.provider))}
                  onSelect={(id) => { setOpenProvider(id); obAdvance('pickProvider'); }}
                  forceOpen={forceProviderMenuOpen}
                  highlight={providerHighlight}
                />

                {/* Selected provider detail */}
                {detail ? (
                  <div data-tour="keysetup" key={detail.id} className="animate-sg-pop" style={{ padding: '20px', border: '1px solid var(--border-strong)', borderRadius: '16px', backgroundColor: 'var(--surface-2)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '11px', marginBottom: '6px' }}>
                      <ProviderLogo p={detail} size={22} />
                      <h3 style={{ margin: 0, fontSize: '19px', fontWeight: 500 }}>{detail.name}</h3>
                      {activeCredential?.provider === detail.id ? (
                        <span className="sg-mono" style={{ padding: '3px 8px', borderRadius: '999px', fontSize: '10px', letterSpacing: '.05em', backgroundColor: 'var(--surface-3)', color: 'var(--text)' }}>Active</span>
                      ) : detailCredential ? (
                        <button
                          disabled={saving}
                          onClick={async () => {
                          setSaving(true); clearError();
                          try {
                            await selectCredential(detailCredential.id);
                          } catch {
                            // The shared error dialog already contains the user-facing failure.
                          } finally { setSaving(false); }
                          }}
                          style={{ padding: '3px 8px', borderRadius: '999px', fontSize: '10px', letterSpacing: '.05em', border: '1px solid var(--border)', backgroundColor: 'transparent', color: 'var(--text)', cursor: 'pointer', fontFamily: 'var(--font-mono)', textTransform: 'uppercase' }}
                        >Set Active</button>
                      ) : null}
                    </div>
                    <p style={{ margin: '0 0 20px', fontSize: '15px', fontStyle: 'italic', color: 'var(--text-dim)', lineHeight: 1.5 }}>{detail.blurb}</p>

                    <div className="sg-mono" style={{ fontSize: '10px', letterSpacing: '.13em', textTransform: 'uppercase', color: 'var(--text-faint)', marginBottom: '12px' }}>How to get your key</div>
                    <ol style={{ margin: '0 0 16px', paddingLeft: '18px', fontSize: '14.5px', lineHeight: 1.7, color: 'var(--text)' }}>
                      <li>Open the <a href={detail.url} target="_blank" rel="noopener noreferrer" style={{ textDecoration: 'underline', textUnderlineOffset: '2px', color: 'var(--accent-2)' }}>{detail.name} console</a> and sign in.</li>
                      <li>Create a new secret key (it starts with <span className="sg-mono" style={{ fontSize: '12px', padding: '1px 5px', borderRadius: '4px', backgroundColor: 'var(--surface-3)' }}>{detail.prefix}</span>).</li>
                      <li>Copy it and paste it below — keys are stored to your account only.</li>
                    </ol>
                    <a href={detail.url} target="_blank" rel="noopener noreferrer" style={{ display: 'inline-flex', alignItems: 'center', gap: '7px', marginBottom: '20px', height: '36px', padding: '0 14px', border: '1px solid var(--border-strong)', borderRadius: '9px', backgroundColor: 'var(--surface)', color: 'var(--text)', fontFamily: 'var(--font-mono)', fontSize: '12px', textDecoration: 'none' }}>
                      Open {detail.name} keys
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" /><polyline points="15 3 21 3 21 9" /><line x1="10" y1="14" x2="21" y2="3" /></svg>
                    </a>
                    <div style={{ marginBottom: '18px', fontSize: '12.5px', fontStyle: 'italic', color: 'var(--text-faint)', lineHeight: 1.5 }}>{detail.docHint}</div>

                    <label className="sg-mono" style={{ display: 'block', fontSize: '10px', letterSpacing: '.13em', textTransform: 'uppercase', color: 'var(--text-faint)', marginBottom: '8px' }}>Paste your API key</label>
                    <div data-tour="keyfield" style={{ display: 'flex', gap: '8px' }}>
                      <input
                        value={currentKeys[detail.id] || ''}
                        onChange={(e) => setCurrentKeys(prev => ({ ...prev, [detail.id]: e.target.value }))}
                        type="password"
                        placeholder={detail.prefix}
                        className="sg-mono"
                        style={{ flex: 1, height: '42px', padding: '0 13px', border: '1px solid var(--border-strong)', backgroundColor: 'var(--surface)', color: 'var(--text)', borderRadius: '10px', fontSize: '13px', outline: 'none' }}
                      />
                      <button
                        disabled={saving || !currentKeys[detail.id]?.trim()}
                        onClick={async () => {
                          const apiKey = currentKeys[detail.id]?.trim();
                          if (!apiKey) return;
                          setSaving(true); clearError();
                          try {
                            await saveCredential(detail.id as ProviderCredential['provider'], apiKey);
                            setCurrentKeys((prev) => ({ ...prev, [detail.id]: '' }));
                            obAdvance('saveKey');
                          } catch {
                            // The shared error dialog already contains the user-facing failure.
                          } finally { setSaving(false); }
                        }}
                        style={{ height: '42px', padding: '0 18px', border: 'none', borderRadius: '10px', backgroundColor: 'var(--accent)', color: '#fff', fontFamily: 'var(--font-mono)', fontSize: '12.5px', fontWeight: 500, cursor: 'pointer' }}
                      >
                        {saving ? 'Saving…' : 'Save'}
                      </button>
                    </div>
                    {credentials.some((credential) => credential.provider === detail.id && credential.status === 'active') && (
                      <button
                        onClick={() => {
                          const credential = activeCredential?.provider === detail.id
                            ? activeCredential
                            : detailCredential;
                          if (credential) void disableCredential(credential.id).catch(() => undefined);
                        }}
                        style={{ display: 'inline-flex', alignItems: 'center', gap: '7px', marginTop: '12px', height: '34px', padding: '0 13px', border: '1px solid var(--border)', borderRadius: '9px', backgroundColor: 'transparent', color: 'var(--color-danger)', fontFamily: 'var(--font-mono)', fontSize: '12px', cursor: 'pointer' }}
                      >
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9"><polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" /><line x1="10" y1="11" x2="10" y2="17" /><line x1="14" y1="11" x2="14" y2="17" /></svg>
                        Disable key
                      </button>
                    )}
                  </div>
                ) : (
                  <div style={{ padding: '28px 20px', border: '1px dashed var(--border-strong)', borderRadius: '16px', textAlign: 'center', fontSize: '13.5px', color: 'var(--text-faint)' }}>
                    Choose a provider from the dropdown to see how to get its key.
                  </div>
                )}
              </div>
            ) : (
              <>
                <div style={{ marginBottom: '32px' }}>
                  <label className="sg-mono" style={{ display: 'block', fontSize: '10px', letterSpacing: '.13em', textTransform: 'uppercase', color: 'var(--text-faint)', marginBottom: '12px' }}>Theme</label>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    {(['system', 'light', 'dark'] as Theme[]).map((t) => (
                      <button
                        key={t}
                        onClick={() => setTheme(t)}
                        style={{
                          flex: 1,
                          height: '42px',
                          border: theme === t ? '1px solid var(--accent)' : '1px solid var(--border)',
                          backgroundColor: theme === t ? 'var(--surface-2)' : 'var(--surface)',
                          color: theme === t ? 'var(--text)' : 'var(--text-dim)',
                          borderRadius: '10px',
                          fontSize: '13.5px',
                          fontWeight: 500,
                          cursor: 'pointer',
                          textTransform: 'capitalize'
                        }}
                      >
                        {t}
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="sg-mono" style={{ display: 'block', fontSize: '10px', letterSpacing: '.13em', textTransform: 'uppercase', color: 'var(--text-faint)', marginBottom: '12px' }}>Accent Color</label>
                  <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                    {ACCENT_COLORS.map((c) => (
                      <button
                        key={c}
                        onClick={() => setAccent(c)}
                        style={{
                          width: '36px',
                          height: '36px',
                          borderRadius: '50%',
                          backgroundColor: c,
                          border: accent === c ? '2px solid var(--text)' : '2px solid transparent',
                          outline: '2px solid transparent',
                          cursor: 'pointer'
                        }}
                      />
                    ))}
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

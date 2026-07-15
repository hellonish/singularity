'use client';

import { useRouter } from 'next/navigation';
import { useAppStore } from '@/store/app-store';
import { logout } from '@/lib/auth';
import { useAuthSession } from '@/components/auth/auth-guard';

function accountInitial(name: string): string {
  return name.trim().charAt(0).toLocaleUpperCase() || '?';
}

export function TopChrome() {
  const router = useRouter();
  const { user, isDemo } = useAuthSession();
  const { view, setView, setSettingsOpen, userMenuOpen, setUserMenuOpen, chatCollapsed, obAdvance } = useAppStore();

  const accountName = isDemo
    ? 'Demo User'
    : user?.display_name?.trim() || user?.email || 'Account';
  const accountEmail = isDemo ? 'Not signed in' : user?.email;

  const rightOffset = view === 'report' ? (chatCollapsed ? 56 : 400) : 0;

  const handleBackToGrid = () => {
    setView('grid');
  };

  const handleLogout = async () => {
    setUserMenuOpen(false);
    if (typeof window !== 'undefined') sessionStorage.removeItem('singularity:demo');
    await logout();
    router.replace('/login');
  };

  return (
    <header style={{ position: 'absolute', top: 0, left: 0, right: rightOffset, zIndex: 25, display: 'flex', alignItems: 'center', gap: '8px', height: view === 'run' ? '58px' : '72px', padding: '0 18px', pointerEvents: 'none' }}>
      {view === 'report' && (
        <button
          onClick={handleBackToGrid}
          style={{ pointerEvents: 'auto', display: 'flex', alignItems: 'center', gap: '7px', height: '34px', padding: '0 13px', border: '1px solid var(--border)', backgroundColor: 'var(--surface)', color: 'var(--text-dim)', borderRadius: '999px', cursor: 'pointer', fontSize: '12px' }}
          className="sg-mono"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="15 18 9 12 15 6" /></svg>Projects
        </button>
      )}
      
      <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '8px', pointerEvents: 'auto' }}>


        <div style={{ position: 'relative' }}>
          <button
            data-tour="settings"
            onClick={() => setUserMenuOpen(!userMenuOpen)}
            title="Account"
            style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: '36px', height: '36px', borderRadius: '999px', backgroundColor: 'var(--accent-soft)', color: 'var(--accent-2)', fontWeight: 500, fontSize: '15px', cursor: 'pointer', border: '1px solid var(--border)', paddingTop: '2px' }}
          >
            {accountInitial(accountName)}
          </button>
          {userMenuOpen && (
            <>
              <div onClick={() => setUserMenuOpen(false)} style={{ position: 'fixed', inset: 0, zIndex: 40 }}></div>
              <div style={{ position: 'absolute', top: 'calc(100% + 8px)', right: 0, width: '236px', backgroundColor: 'var(--surface)', border: '1px solid var(--border-strong)', borderRadius: '14px', boxShadow: 'var(--shadow)', padding: '6px', zIndex: 50 }} className="animate-sg-pop">
                <div style={{ padding: '10px 11px 11px', borderBottom: '1px solid var(--border)', marginBottom: '5px' }}>
                  <div style={{ fontSize: '14.5px', fontWeight: 500, color: 'var(--text)' }}>{accountName}</div>
                  {accountEmail && (
                    <div className="sg-mono" style={{ fontSize: '11px', color: 'var(--text-faint)', marginTop: '2px' }}>{accountEmail}</div>
                  )}
                </div>
                <button
                  data-tour="menu-settings"
                  onClick={() => { setUserMenuOpen(false); setSettingsOpen(true); obAdvance('openSettings'); }}
                  style={{ display: 'flex', alignItems: 'center', gap: '10px', width: '100%', padding: '9px 11px', border: 'none', backgroundColor: 'transparent', color: 'var(--text)', borderRadius: '9px', cursor: 'pointer', fontSize: '14px', textAlign: 'left' }}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7"><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" /></svg>
                  Settings
                </button>
                <button
                  onClick={handleLogout}
                  style={{ display: 'flex', alignItems: 'center', gap: '10px', width: '100%', padding: '9px 11px', border: 'none', borderTop: '1px solid var(--border)', marginTop: '5px', backgroundColor: 'transparent', color: 'var(--color-danger)', borderRadius: '9px', cursor: 'pointer', fontSize: '14px', textAlign: 'left' }}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" /><polyline points="16 17 21 12 16 7" /><line x1="21" y1="12" x2="9" y2="12" /></svg>
                  {isDemo ? 'Exit demo' : 'Log out'}
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  );
}

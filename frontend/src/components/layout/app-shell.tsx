'use client';

import { useEffect, useRef } from 'react';
import { useAppStore, applyThemeAndAccent } from '@/store/app-store';
import { Sidebar } from './sidebar';
import { TopChrome } from './top-chrome';
import { SettingsModal } from '@/components/modals/settings-modal';
import { ErrorModal } from '@/components/modals/error-modal';
import { Spotlight } from '@/components/onboarding/spotlight';
import { WorkspaceProvider } from '@/components/workspace-provider';
import { useIsMobile } from '@/lib/use-media-query';

export function AppShell({ children }: { children: React.ReactNode }) {
  const { theme, accent, mobileSidebarOpen, setMobileSidebarOpen } = useAppStore();
  const themeRef = useRef<HTMLDivElement>(null);
  const isMobile = useIsMobile();

  useEffect(() => {
    applyThemeAndAccent(theme, accent);

    if (theme === 'system') {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      const handleChange = () => applyThemeAndAccent('system', accent);
      mediaQuery.addEventListener('change', handleChange);
      return () => mediaQuery.removeEventListener('change', handleChange);
    }
  }, [theme, accent]);

  return (
    <div
      ref={themeRef}
      className="dashboard-root"
      style={{
        display: 'flex',
        height: '100vh',
        width: '100%',
        overflow: 'hidden',
        backgroundColor: 'var(--bg)',
        color: 'var(--text)',
        fontFamily: 'var(--font-sans)',
        transition: 'background 0.3s, color 0.3s'
      }}
    >
      <WorkspaceProvider>
      {isMobile ? (
        <>
          {mobileSidebarOpen && (
            <div
              onClick={() => setMobileSidebarOpen(false)}
              aria-hidden="true"
              className="animate-sg-scrim"
              style={{ position: 'fixed', inset: 0, zIndex: 60, background: 'rgba(6,9,14,0.5)' }}
            />
          )}
          <div
            style={{
              position: 'fixed',
              top: 0,
              bottom: 0,
              left: 0,
              zIndex: 61,
              transform: mobileSidebarOpen ? 'translateX(0)' : 'translateX(-100%)',
              transition: 'transform .22s ease',
              boxShadow: mobileSidebarOpen ? '0 0 40px rgba(0,0,0,0.35)' : 'none',
            }}
          >
            <Sidebar forceOpen onNavigate={() => setMobileSidebarOpen(false)} />
          </div>
        </>
      ) : (
        <Sidebar />
      )}
      <main
        data-screen-label="Workspace"
        style={{
          position: 'relative',
          flex: 1,
          minWidth: 0,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          backgroundColor: 'var(--bg)'
        }}
      >
        <TopChrome />
        {children}
        <SettingsModal />
        <ErrorModal />
        <Spotlight />
      </main>
      </WorkspaceProvider>
    </div>
  );
}

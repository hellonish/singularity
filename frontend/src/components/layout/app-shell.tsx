'use client';

import { useEffect, useRef } from 'react';
import { useAppStore, applyThemeAndAccent } from '@/store/app-store';
import { Sidebar } from './sidebar';
import { TopChrome } from './top-chrome';
import { SettingsModal } from '@/components/modals/settings-modal';
import { ErrorModal } from '@/components/modals/error-modal';
import { Spotlight } from '@/components/onboarding/spotlight';
import { WorkspaceProvider } from '@/components/workspace-provider';

export function AppShell({ children }: { children: React.ReactNode }) {
  const { theme, accent } = useAppStore();
  const themeRef = useRef<HTMLDivElement>(null);

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
      style={{
        display: 'flex',
        height: '100vh',
        width: '100%',
        overflow: 'hidden',
        backgroundColor: 'var(--bg)',
        color: 'var(--text)',
        fontFamily: 'var(--font-serif)',
        transition: 'background 0.3s, color 0.3s'
      }}
    >
      <WorkspaceProvider>
      <Sidebar />
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

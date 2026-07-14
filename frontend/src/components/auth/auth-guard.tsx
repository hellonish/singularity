'use client';

import { createContext, useContext, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  AuthRequestError,
  getCurrentUser,
  isAuthenticated,
  type AuthenticatedUser,
} from '@/lib/auth';

// Gates the dashboard: a real session (bearer tokens in localStorage) passes
// through. A visitor who chose "Skip for now — explore the demo" on the login
// screen is let through in demo mode. Everyone else is bounced to /login.
//
// This runs client-side only. The tokens live in localStorage, which the server
// can't read, so a server-side redirect isn't possible without a cookie mode.
interface AuthSession {
  user: AuthenticatedUser | null;
  isDemo: boolean;
}

const AuthSessionContext = createContext<AuthSession | null>(null);

export function useAuthSession(): AuthSession {
  const session = useContext(AuthSessionContext);
  if (!session) throw new Error('useAuthSession must be used inside AuthGuard');
  return session;
}

type SessionState =
  | { status: 'checking' }
  | { status: 'authenticated'; user: AuthenticatedUser }
  | { status: 'demo' }
  | { status: 'unauthenticated' }
  | { status: 'error' };

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [session, setSession] = useState<SessionState>({ status: 'checking' });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;

    async function resolveSession() {
      if (!isAuthenticated()) {
        if (sessionStorage.getItem('singularity:demo') === '1') {
          setSession({ status: 'demo' });
          return;
        }
        setSession({ status: 'unauthenticated' });
        router.replace('/login');
        return;
      }

      try {
        const user = await getCurrentUser();
        if (!cancelled) setSession({ status: 'authenticated', user });
      } catch (error) {
        if (cancelled) return;
        if (error instanceof AuthRequestError && error.status === 401) {
          setSession({ status: 'unauthenticated' });
          router.replace('/login');
          return;
        }
        setSession({ status: 'error' });
      }
    }

    void resolveSession();
    return () => {
      cancelled = true;
    };
  }, [attempt, router]);

  if (session.status === 'checking' || session.status === 'unauthenticated') return null;

  if (session.status === 'error') {
    return (
      <main style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', background: 'var(--bg)', color: 'var(--text)' }}>
        <div style={{ textAlign: 'center' }}>
          <p>We couldn&apos;t load your account.</p>
          <button onClick={() => { setSession({ status: 'checking' }); setAttempt((value) => value + 1); }}>
            Retry
          </button>
        </div>
      </main>
    );
  }

  const value: AuthSession = session.status === 'demo'
    ? { user: null, isDemo: true }
    : { user: session.user, isDemo: false };

  return <AuthSessionContext.Provider value={value}>{children}</AuthSessionContext.Provider>;
}

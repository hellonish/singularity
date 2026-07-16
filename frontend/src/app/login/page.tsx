"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAppStore } from "@/store/app-store";
import { AppLogoMark } from "@/components/app-logo";
import { googleLogin, isAuthenticated } from "@/lib/auth";
import { isGoogleConfigured, requestGoogleIdToken } from "@/lib/google";
import { ErrorDialog } from "@/components/modals/error-modal";

export default function LoginPage() {
  const router = useRouter();
  const { theme, accent } = useAppStore();
  const [signingIn, setSigningIn] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Already signed in? Skip the login screen.
  useEffect(() => {
    if (isAuthenticated()) router.replace("/dashboard");
  }, [router]);

  const goBack = () => router.push("/");

  const signInWithGoogle = async () => {
    if (signingIn) return;
    setError(null);
    if (!isGoogleConfigured()) {
      setError("Google sign-in is not configured. Set NEXT_PUBLIC_GOOGLE_CLIENT_ID.");
      return;
    }
    setSigningIn(true);
    try {
      const idToken = await requestGoogleIdToken();
      await googleLogin(idToken);
      router.replace("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign-in failed. Please try again.");
      setSigningIn(false);
    }
  };

  return (
    <div data-app-theme={theme} style={{ 
      minHeight: '100vh', 
      background: 'var(--bg)', 
      color: 'var(--text)', 
      fontFamily: "'Newsreader', Georgia, serif",
      '--accent': accent, 
      '--accent-soft': `${accent}22` 
    } as React.CSSProperties}>
      <style dangerouslySetInnerHTML={{ __html: `
        body { margin: 0; background: var(--bg); color: var(--text); -webkit-font-smoothing: antialiased; }
        .lp-mono { font-family: 'JetBrains Mono', monospace; }
        @keyframes lp-rise { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: none; } }
      ` }} />

      <div data-screen-label="Google sign-in" style={{ position: 'relative', minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 24, overflow: 'hidden' }}>
        <div style={{ pointerEvents: 'none', position: 'absolute', left: '50%', top: '34%', width: 560, height: 560, transform: 'translate(-50%,-50%)', borderRadius: '50%', background: 'var(--accent-soft)', filter: 'blur(120px)', opacity: 0.7 }}></div>

        <button onClick={goBack} className="lp-mono" style={{ position: 'absolute', top: 26, left: 26, display: 'flex', alignItems: 'center', gap: 8, height: 38, padding: '0 15px', border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text-dim)', borderRadius: 999, cursor: 'pointer', fontSize: 12 }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="15 18 9 12 15 6"/></svg>Back
        </button>

        <div style={{ position: 'relative', zIndex: 1, width: 'min(420px,100%)', textAlign: 'center', animation: 'lp-rise .5s ease both' }}>
          <AppLogoMark width={52} height={52} style={{ margin: '0 auto 20px', display: 'block' }} />
          <h1 style={{ margin: 0, fontSize: 32, fontWeight: 300, letterSpacing: '-.02em', lineHeight: 1.1 }}>Welcome to Singularity</h1>
          <p style={{ margin: '12px 0 0', fontSize: 16, fontWeight: 300, lineHeight: 1.6, color: 'var(--text-dim)' }}>
            Sign in with Google to open your workspace. Reports, chats, and provider keys are stored to your account only.
          </p>

          <div style={{ marginTop: 32, background: 'var(--surface)', border: '1px solid var(--border-strong)', borderRadius: 20, boxShadow: 'var(--shadow)', padding: 24 }}>
            <button onClick={signInWithGoogle} disabled={signingIn} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12, width: '100%', height: 52, border: '1px solid var(--border-strong)', background: 'var(--surface-2)', color: 'var(--text)', borderRadius: 12, cursor: signingIn ? 'wait' : 'pointer', opacity: signingIn ? 0.7 : 1, fontFamily: "'Newsreader', serif", fontSize: 16, fontWeight: 400 }}>
              <svg width="20" height="20" viewBox="0 0 24 24">
                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/>
                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
              </svg>
              {signingIn ? "Signing in…" : "Continue with Google"}
            </button>
          </div>
          <p className="lp-mono" style={{ margin: '20px auto 0', maxWidth: '34ch', fontSize: 10.5, lineHeight: 1.6, color: 'var(--text-faint)' }}>
            By continuing you agree to the Terms of Service and Privacy Policy.
          </p>
        </div>
      </div>
      <ErrorDialog error={error} onDismiss={() => setError(null)} />
    </div>
  );
}

// Loads Google Identity Services (GIS) and requests a Google `id_token`.
//
// We use the GIS "ID token" flow: `google.accounts.id` issues a signed JWT
// (`credential`) that our backend verifies with the Google client id. That JWT
// is exactly the `id_token` `/auth/google` expects — no OAuth server round-trip
// or client secret lives in the browser.

const GIS_SRC = 'https://accounts.google.com/gsi/client';

const CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID ?? '';

interface CredentialResponse {
  credential?: string;
}

interface GoogleAccountsId {
  initialize(config: {
    client_id: string;
    callback: (response: CredentialResponse) => void;
    auto_select?: boolean;
    cancel_on_tap_outside?: boolean;
  }): void;
  prompt(momentListener?: (notification: PromptMomentNotification) => void): void;
  renderButton(parent: HTMLElement, options: Record<string, unknown>): void;
}

interface PromptMomentNotification {
  isNotDisplayed(): boolean;
  isSkippedMoment(): boolean;
  isDismissedMoment(): boolean;
  getNotDisplayedReason(): string;
  getSkippedReason(): string;
}

declare global {
  interface Window {
    google?: { accounts: { id: GoogleAccountsId } };
  }
}

export function isGoogleConfigured(): boolean {
  return CLIENT_ID.length > 0;
}

let scriptPromise: Promise<void> | null = null;

function loadScript(): Promise<void> {
  if (typeof window === 'undefined') return Promise.reject(new Error('no window'));
  if (window.google?.accounts?.id) return Promise.resolve();
  if (scriptPromise) return scriptPromise;

  scriptPromise = new Promise<void>((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(`script[src="${GIS_SRC}"]`);
    if (existing) {
      existing.addEventListener('load', () => resolve());
      existing.addEventListener('error', () => reject(new Error('Failed to load Google Identity Services')));
      return;
    }
    const script = document.createElement('script');
    script.src = GIS_SRC;
    script.async = true;
    script.defer = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error('Failed to load Google Identity Services'));
    document.head.appendChild(script);
  });
  return scriptPromise;
}

/**
 * Trigger the Google sign-in prompt and resolve with the returned `id_token`.
 * Rejects if GIS is misconfigured, fails to load, or the user dismisses the
 * prompt without completing sign-in.
 */
export async function requestGoogleIdToken(): Promise<string> {
  if (!isGoogleConfigured()) {
    throw new Error('Google sign-in is not configured: set NEXT_PUBLIC_GOOGLE_CLIENT_ID');
  }
  await loadScript();
  const accountsId = window.google?.accounts?.id;
  if (!accountsId) throw new Error('Google Identity Services unavailable');

  return new Promise<string>((resolve, reject) => {
    accountsId.initialize({
      client_id: CLIENT_ID,
      callback: (response) => {
        if (response.credential) resolve(response.credential);
        else reject(new Error('No credential returned from Google'));
      },
      cancel_on_tap_outside: true,
    });
    accountsId.prompt((notification) => {
      // The One Tap prompt can be suppressed (cooldown, no session, opt-out).
      // Surface that as a rejection so the caller can show an error rather than
      // hang forever waiting on a callback that will never fire.
      if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
        reject(
          new Error(
            `Google prompt not shown (${notification.getNotDisplayedReason?.() ?? notification.getSkippedReason?.() ?? 'unknown'})`,
          ),
        );
      }
    });
  });
}

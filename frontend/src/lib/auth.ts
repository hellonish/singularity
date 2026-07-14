// Client-side session for the bearer-token auth flow served by `/auth/*`.
//
// The backend (default `auth_mode: bearer`) verifies a signed access JWT on the
// `Authorization` header. Access tokens are short-lived (~15 min); the opaque
// refresh token rotates on every use. This module owns:
//   - persisting the token pair (localStorage, so a reload stays signed in),
//   - exchanging a Google `id_token` for a pair (`googleLogin`),
//   - rotating the pair (`refresh`) and revoking it (`logout`),
//   - `authFetch`, a `fetch` wrapper that attaches the access token and, on a
//     single 401, transparently refreshes once and retries.
//
// Tokens live in localStorage rather than an httpOnly cookie because the API
// authenticates via the Authorization header, not cookies. That trades some
// XSS hardening for a simpler SPA flow; revisit if the API grows a cookie mode.

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? '';

const ACCESS_KEY = 'singularity:access_token';
const REFRESH_KEY = 'singularity:refresh_token';

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  token_type: 'bearer';
}

export interface AuthenticatedUser {
  id: string;
  email: string | null;
  display_name: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export class AuthRequestError extends Error {
  constructor(public readonly status: number) {
    super(`Unable to load the current user (${status})`);
    this.name = 'AuthRequestError';
  }
}

function hasStorage(): boolean {
  return typeof window !== 'undefined';
}

export function getAccessToken(): string | null {
  return hasStorage() ? localStorage.getItem(ACCESS_KEY) : null;
}

export function getRefreshToken(): string | null {
  return hasStorage() ? localStorage.getItem(REFRESH_KEY) : null;
}

export function isAuthenticated(): boolean {
  return getAccessToken() !== null;
}

function storeTokens(pair: TokenPair): void {
  if (!hasStorage()) return;
  localStorage.setItem(ACCESS_KEY, pair.access_token);
  localStorage.setItem(REFRESH_KEY, pair.refresh_token);
}

function clearTokens(): void {
  if (!hasStorage()) return;
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

/** Exchange a Google id_token for our token pair. Throws on failure. */
export async function googleLogin(idToken: string): Promise<TokenPair> {
  const response = await fetch(`${API_BASE}/auth/google`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id_token: idToken }),
  });
  if (!response.ok) {
    const detail = await response.text().catch(() => '');
    throw new Error(`Google sign-in failed (${response.status}): ${detail}`);
  }
  const pair = (await response.json()) as TokenPair;
  storeTokens(pair);
  return pair;
}

// Serialize concurrent refreshes: a burst of 401s must rotate the token only
// once, or the losers would present an already-rotated token and trip the
// backend's reuse detection (which revokes the whole family).
let inflightRefresh: Promise<string | null> | null = null;

/** Rotate the token pair, returning the new access token (or null on failure). */
export async function refresh(): Promise<string | null> {
  if (inflightRefresh) return inflightRefresh;

  inflightRefresh = (async () => {
    const refreshToken = getRefreshToken();
    if (!refreshToken) return null;
    try {
      const response = await fetch(`${API_BASE}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!response.ok) {
        // The refresh token is dead (expired, rotated, or revoked). Drop the
        // session so the app routes back to login.
        clearTokens();
        return null;
      }
      const pair = (await response.json()) as TokenPair;
      storeTokens(pair);
      return pair.access_token;
    } catch {
      // Network failure: keep the tokens so a later retry can still succeed.
      return null;
    } finally {
      inflightRefresh = null;
    }
  })();

  return inflightRefresh;
}

/** Revoke the refresh token server-side (best effort) and clear local state. */
export async function logout(): Promise<void> {
  const refreshToken = getRefreshToken();
  clearTokens();
  if (!refreshToken) return;
  try {
    await fetch(`${API_BASE}/auth/logout`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
  } catch {
    // Best effort; the token still expires server-side on its own TTL.
  }
}

function withAuthHeader(init: RequestInit, token: string): RequestInit {
  const headers = new Headers(init.headers);
  headers.set('Authorization', `Bearer ${token}`);
  return { ...init, headers };
}

/**
 * `fetch` that attaches the access token and, on a 401, refreshes once and
 * retries. A persistent 401 (or missing session) is returned to the caller,
 * who should route the user back to login.
 */
export async function authFetch(input: string, init: RequestInit = {}): Promise<Response> {
  const url = input.startsWith('http') ? input : `${API_BASE}${input}`;
  const token = getAccessToken();
  if (!token) {
    // No session at all; let the caller handle the 401-equivalent.
    return new Response(null, { status: 401, statusText: 'Not authenticated' });
  }

  const response = await fetch(url, withAuthHeader(init, token));
  if (response.status !== 401) return response;

  const refreshed = await refresh();
  if (!refreshed) return response;
  return fetch(url, withAuthHeader(init, refreshed));
}

/** Load the user represented by the current bearer session. */
export async function getCurrentUser(): Promise<AuthenticatedUser> {
  const response = await authFetch('/users/me');
  if (!response.ok) {
    throw new AuthRequestError(response.status);
  }
  return (await response.json()) as AuthenticatedUser;
}

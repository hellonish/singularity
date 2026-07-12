import NextAuth from "next-auth";
import Google from "next-auth/providers/google";
import type { NextAuthConfig } from "next-auth";

import {
  normalizeBackendUrlForNodeFetch,
  publicApiBaseUrl,
} from "@/lib/public_api_base_url";

/** True when fetch failed before an HTTP status (network / TLS / reset). */
function isTransientNodeFetchError(e: unknown): boolean {
  const msg = e instanceof Error ? e.message : String(e);
  let cause: unknown =
    e && typeof e === "object" && "cause" in e
      ? (e as { cause?: unknown }).cause
      : undefined;
  const parts = [msg];
  for (let i = 0; i < 3 && cause instanceof Error; i++) {
    parts.push(cause.message, String((cause as Error & { code?: string }).code ?? ""));
    cause = "cause" in cause ? (cause as { cause?: unknown }).cause : undefined;
  }
  const s = parts.join(" ").toLowerCase();
  return (
    s.includes("econnreset") ||
    s.includes("econnrefused") ||
    s.includes("etimedout") ||
    s.includes("socket hang up") ||
    s.includes("fetch failed")
  );
}

async function fetchWithTransientRetry(
  url: string,
  init: RequestInit,
  attempts = 2,
): Promise<Response> {
  let last: unknown;
  for (let i = 0; i < attempts; i++) {
    try {
      return await fetch(url, init);
    } catch (e) {
      last = e;
      if (!isTransientNodeFetchError(e) || i === attempts - 1) {
        throw e;
      }
    }
  }
  throw last;
}

/** True when Node runtime (not Edge) and `/.dockerenv` exists — avoids `fs` on Edge middleware bundles. */
function isDockerContainerNode(): boolean {
  if (typeof process === "undefined" || !process.versions?.node) return false;
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { existsSync } = require("node:fs") as typeof import("node:fs");
    return existsSync("/.dockerenv");
  } catch {
    return false;
  }
}

/**
 * URL the Next.js server uses for `/api/v1/auth/*` (JWT callback runs on the server).
 * - Prefer INTERNAL_API_URL when set (Docker / split deploy).
 * - If the process runs inside Docker and the public URL still points at localhost,
 *   rewrite the host to host.docker.internal so the container can reach the host API.
 */
function resolveBackendFetchBase(): string {
  const raw = process.env.INTERNAL_API_URL;
  if (typeof raw === "string") {
    const t = raw.trim().replace(/\/+$/, "");
    if (t.length > 0) {
      return normalizeBackendUrlForNodeFetch(t);
    }
  }

  const pub = publicApiBaseUrl();
  if (isDockerContainerNode()) {
    try {
      const u = new URL(pub);
      if (u.hostname === "localhost" || u.hostname === "127.0.0.1") {
        u.hostname = "host.docker.internal";
        return u.toString().replace(/\/+$/, "");
      }
    } catch {
      /* ignore */
    }
    return "http://host.docker.internal:8000";
  }

  return normalizeBackendUrlForNodeFetch(pub);
}

function applyBackendTokenPayload(
  token: import("next-auth/jwt").JWT,
  data: { access_token?: string; refresh_token?: string; expires_in?: number },
) {
  if (data.access_token) token.accessToken = data.access_token;
  if (data.refresh_token) token.refreshToken = data.refresh_token;
  const sec =
    typeof data.expires_in === "number" && Number.isFinite(data.expires_in)
      ? data.expires_in
      : 900;
  token.accessTokenExpires = Date.now() + sec * 1000;
  delete token.error;
}

type BackendTokenPayload = {
  access_token?: string;
  refresh_token?: string;
  expires_in?: number;
};

/**
 * Refresh rotation is single-use on the server; concurrent JWT callbacks must share
 * one in-flight POST. Store the map on `globalThis` so Next.js dev HMR does not reset
 * the map mid-flight (which previously allowed a second refresh with an already-rotated
 * token and triggered family-wide revocation).
 */
const REFRESH_INFLIGHT_KEY = "__singularity_auth_refresh_inflight_v1" as const;

function getRefreshInflightMap(): Map<string, Promise<BackendRotateResult>> {
  const g = globalThis as unknown as Record<
    string,
    Map<string, Promise<BackendRotateResult>> | undefined
  >;
  if (!g[REFRESH_INFLIGHT_KEY]) {
    g[REFRESH_INFLIGHT_KEY] = new Map();
  }
  return g[REFRESH_INFLIGHT_KEY]!;
}

type BackendRotateResult =
  | { kind: "ok"; data: BackendTokenPayload }
  | { kind: "auth_error" }
  | { kind: "transient" };

async function rotateBackendRefresh(refreshToken: string): Promise<BackendRotateResult> {
  const inflight = getRefreshInflightMap();
  let pending = inflight.get(refreshToken);
  if (!pending) {
    pending = (async (): Promise<BackendRotateResult> => {
      try {
        const res = await fetchWithTransientRetry(
          `${resolveBackendFetchBase()}/api/v1/auth/refresh`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ refresh_token: refreshToken }),
          },
        );
        if (!res.ok) {
          // Only treat definitive auth failures as "log out". 5xx / network-ish codes
          // leave refresh + access cookies intact so the next JWT tick can retry.
          if (res.status === 401 || res.status === 403) {
            return { kind: "auth_error" };
          }
          return { kind: "transient" };
        }
        const data = (await res.json()) as BackendTokenPayload;
        return { kind: "ok", data };
      } catch {
        return { kind: "transient" };
      } finally {
        inflight.delete(refreshToken);
      }
    })();
    inflight.set(refreshToken, pending);
  }
  return pending;
}

export const authConfig: NextAuthConfig = {
  providers: [
    Google({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    }),
  ],
  callbacks: {
    async jwt({ token, account, user }) {
      if (user?.email) {
        token.email = user.email;
      }
      if (account?.id_token) {
        delete token.error;
        try {
          const apiBase = resolveBackendFetchBase();
          const res = await fetchWithTransientRetry(`${apiBase}/api/v1/auth/google`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ id_token: account.id_token }),
          });
          if (res.ok) {
            const data = await res.json();
            applyBackendTokenPayload(token, data);
          } else {
            const errBody = await res.text();
            console.error("Backend auth exchange failed:", res.status, errBody);
            token.error = "BackendSignInError";
          }
        } catch (e) {
          console.error("Backend auth exchange error:", e);
          token.error = "BackendSignInError";
        }
      }

      const expRaw = token.accessTokenExpires;
      const exp = expRaw != null ? Number(expRaw) : NaN;
      const expiryTrusted = Number.isFinite(exp);
      const accessMissing = !token.accessToken;
      const accessTimedOut =
        expiryTrusted && Date.now() > exp - 60_000;
      const shouldRefreshBackend =
        Boolean(token.refreshToken) && (accessMissing || accessTimedOut);

      if (shouldRefreshBackend && typeof token.refreshToken === "string") {
        const result = await rotateBackendRefresh(token.refreshToken);
        if (result.kind === "ok") {
          applyBackendTokenPayload(token, result.data);
        } else if (result.kind === "auth_error") {
          console.error("Token refresh rejected — session cleared");
          delete token.accessToken;
          delete token.accessTokenExpires;
          delete token.refreshToken;
          token.error = "RefreshAccessTokenError";
        } else {
          console.warn(
            "[auth] Refresh temporarily unavailable (backend or network); keeping session for retry",
          );
        }
      }

      return token;
    },
    async session({ session, token }) {
      const email =
        session.user?.email ?? (typeof token.email === "string" ? token.email : undefined);
      return {
        ...session,
        user: session.user
          ? { ...session.user, ...(email ? { email } : {}) }
          : session.user,
        accessToken: token.accessToken ?? undefined,
        error: token.error,
      };
    },
  },
  pages: {
    signIn: "/",
  },
  secret: process.env.NEXTAUTH_SECRET,
  trustHost: true,
  debug: process.env.NODE_ENV === "development",
};

export const { handlers, auth, signIn, signOut } = NextAuth(authConfig);

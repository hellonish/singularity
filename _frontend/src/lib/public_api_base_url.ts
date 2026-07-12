/**
 * Base URL for the FastAPI backend as seen from the **browser** (see `api.ts`).
 *
 * Set `NEXT_PUBLIC_API_URL` to a URL the user’s device can reach (often the same
 * host as the Next app, or a public API URL).
 */
export function publicApiBaseUrl(): string {
  const raw = process.env.NEXT_PUBLIC_API_URL;
  if (typeof raw === "string") {
    const t = raw.trim().replace(/\/+$/, "");
    if (t.length > 0) {
      return t;
    }
  }
  return "http://localhost:8000";
}

/**
 * Node/undici `fetch` to `http://localhost:...` can hit IPv6 ::1 while the API
 * listens on IPv4 only, surfacing as ECONNRESET. Use IPv4 loopback for server-side calls.
 * Does not rewrite `host.docker.internal` or other hostnames.
 */
export function normalizeBackendUrlForNodeFetch(base: string): string {
  const t = base.trim().replace(/\/+$/, "");
  try {
    const u = new URL(t);
    if (u.hostname === "localhost") {
      u.hostname = "127.0.0.1";
    }
    return u.toString().replace(/\/+$/, "");
  } catch {
    return t;
  }
}

/**
 * Base URL for FastAPI when **Next.js calls the API on the server** (NextAuth JWT
 * callback: Google exchange and refresh). Defaults to `publicApiBaseUrl()`.
 *
 * When the web app runs in Docker but the API is on the host, set
 * `INTERNAL_API_URL=http://host.docker.internal:8000` (or your compose service
 * name). `NEXT_PUBLIC_API_URL` should still be whatever the browser must use.
 */
export function serverApiBaseUrl(): string {
  const raw = process.env.INTERNAL_API_URL;
  if (typeof raw === "string") {
    const t = raw.trim().replace(/\/+$/, "");
    if (t.length > 0) {
      return normalizeBackendUrlForNodeFetch(t);
    }
  }
  return normalizeBackendUrlForNodeFetch(publicApiBaseUrl());
}

"use client";

import { useState } from "react";
import { signOut, useSession } from "next-auth/react";

import { publicApiBaseUrl } from "@/lib/public_api_base_url";

/**
 * Shown when NextAuth is authenticated but the app has no usable backend JWT
 * (exchange or refresh failed). Offers retry and explicit sign-out instead of
 * immediately signing out (which caused a redirect loop with the landing page).
 */
export function AccountReconnectPrompt() {
  const { update } = useSession();
  const [busy, setBusy] = useState(false);

  return (
    <div
      className="flex h-dvh flex-col items-center justify-center gap-6 px-6"
      style={{ background: "var(--rpt-bg)" }}
    >
      <div className="max-w-md text-center">
        <h1 className="text-lg font-semibold text-[#111827]">Can&apos;t finish sign-in</h1>
        <p className="mt-3 text-sm leading-relaxed text-[#4b5563]">
          You&apos;re signed in with Google, but the Next.js server could not reach
          FastAPI to exchange your session for app tokens. Start the API and check env: the browser
          uses{" "}
          <code className="rounded bg-neutral-200/80 px-1 py-0.5 text-xs">NEXT_PUBLIC_API_URL</code>
          ; sign-in also needs{" "}
          <code className="rounded bg-neutral-200/80 px-1 py-0.5 text-xs">INTERNAL_API_URL</code> when
          the web app runs in Docker (e.g.{" "}
          <code className="rounded bg-neutral-200/80 px-1 py-0.5 text-[10px]">
            http://host.docker.internal:8000
          </code>
          ), because           <code className="rounded bg-neutral-200/80 px-1 py-0.5 text-xs">localhost</code>{" "}
          inside the container is not your host machine. If Next.js runs in Docker and your API is on
          the host, the app also tries{" "}
          <code className="rounded bg-neutral-200/80 px-1 py-0.5 text-[10px]">
            host.docker.internal
          </code>{" "}
          automatically when <code className="rounded bg-neutral-200/80 px-1 py-0.5 text-xs">INTERNAL_API_URL</code>{" "}
          is unset — set it explicitly if your API is another container (e.g. compose service name).
        </p>
        <p className="mt-2 font-mono text-[11px] text-[#6b7280]">
          Browser API base: {publicApiBaseUrl()}
        </p>
      </div>
      <div className="flex flex-wrap items-center justify-center gap-3">
        <button
          type="button"
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            try {
              await update();
            } finally {
              setBusy(false);
            }
          }}
          className="rounded-full bg-[#111827] px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-[#1f2937] disabled:opacity-50"
        >
          {busy ? "Retrying…" : "Retry connection"}
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => void signOut({ callbackUrl: "/" })}
          className="rounded-full border border-neutral-300 bg-white px-5 py-2.5 text-sm font-medium text-[#374151] transition-colors hover:bg-neutral-50 disabled:opacity-50"
        >
          Sign out
        </button>
      </div>
    </div>
  );
}

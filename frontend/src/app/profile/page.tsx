"use client";

import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { UserMenu } from "@/components/user-menu";
import { AppLogoMark } from "@/components/app-logo";
import { AccountReconnectPrompt } from "@/components/account_reconnect_prompt";
import { ProfileLlmKeysSection } from "@/components/profile_llm_keys_section";

export default function ProfilePage() {
  const { status: authStatus, data: session } = useSession();
  const apiReady =
    authStatus === "authenticated" && Boolean(session?.accessToken);
  const router = useRouter();

  if (authStatus === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center" style={{ background: "var(--rpt-bg)" }}>
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-[#6366f1] border-t-transparent" />
      </div>
    );
  }

  if (authStatus === "unauthenticated") { router.push("/"); return null; }

  if (
    authStatus === "authenticated" &&
    (!session?.accessToken || session?.error)
  ) {
    return <AccountReconnectPrompt />;
  }

  return (
    <div className="min-h-screen" style={{ background: "var(--rpt-bg)" }}>
      <header
        className="fixed left-0 right-0 top-0 z-40 grid h-14 w-full grid-cols-[1fr_auto_1fr] items-center gap-2 px-5"
        style={{
          background: "rgba(255,255,255,0.95)",
          borderBottom: "1px solid #e5e2db",
          backdropFilter: "blur(8px)",
        }}
      >
        <div className="flex min-w-0 items-center gap-3">
          <button
            type="button"
            onClick={() => router.push("/dashboard")}
            className="flex shrink-0 items-center gap-1.5 transition-colors"
            style={{ color: "#6b7280", fontFamily: "var(--mono)", fontSize: 12 }}
            onMouseEnter={(e) => (e.currentTarget.style.color = "#1a1a1a")}
            onMouseLeave={(e) => (e.currentTarget.style.color = "#6b7280")}
          >
            <ArrowLeft size={14} />
            Dashboard
          </button>
          <h1
            className="min-w-0 truncate"
            style={{ fontFamily: "var(--mono, monospace)", fontSize: 13, color: "#1a1a1a" }}
          >
            API Keys
          </h1>
        </div>

        <div
          className="flex items-center gap-2 py-1 pl-1 pr-2"
          style={{
            background:
              "radial-gradient(ellipse 140% 200% at 50% 28%, rgba(255,255,255,1) 0%, rgba(255,255,255,0.98) 35%, rgba(255,255,255,0.92) 52%, rgba(255,255,255,0.72) 70%, rgba(255,255,255,0.28) 88%, rgba(255,255,255,0.06) 96%, rgba(255,255,255,0) 100%)",
          }}
        >
          <AppLogoMark className="h-8 w-8 shrink-0 object-contain" />
          <span className="text-base font-semibold tracking-tight text-[#111827]">Singularity</span>
        </div>

        <div className="flex flex-shrink-0 items-center justify-end gap-2">
          <UserMenu />
        </div>
      </header>

      <main className="mx-auto w-full max-w-7xl space-y-10 px-6 pb-8 pt-[calc(3.5rem+2rem)]">
        <ProfileLlmKeysSection apiReady={apiReady} />
      </main>
    </div>
  );
}

"use client";

import { signIn, signOut, useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { motion } from "framer-motion";
import { AppLogoMark } from "@/components/app-logo";
import { publicApiBaseUrl } from "@/lib/public_api_base_url";

export default function LandingPage() {
  const { status, data: session } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (status !== "authenticated") return;
    if (!session?.accessToken || session?.error) return;
    router.push("/dashboard");
  }, [status, session?.accessToken, session?.error, router]);

  const backendBlocked =
    status === "authenticated" &&
    (!session?.accessToken || Boolean(session?.error));

  return (
    <div
      className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden px-6"
      style={{ background: "var(--rpt-bg)" }}
    >
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute left-1/2 top-1/2 h-[520px] w-[520px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-indigo-200/20 blur-[120px]" />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="relative z-10 flex w-full max-w-xl flex-col items-center gap-8 text-center"
      >
        {/* Logo / Brand */}
        <motion.div
          initial={{ scale: 0.9 }}
          animate={{ scale: 1 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="flex items-center gap-3"
        >
          <AppLogoMark className="h-11 w-11 sm:h-12 sm:w-12" priority />
          <h1 className="text-4xl font-semibold tracking-tight text-[#111827] sm:text-5xl">
            Singularity
          </h1>
        </motion.div>

        {/* Tagline */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="max-w-lg text-base leading-7 text-[#374151] sm:text-lg"
        >
          Intelligence Emerges At This Point
        </motion.p>

        {/* Philosophical quote — editorial pull-quote treatment */}
        <motion.blockquote
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.38, duration: 0.55 }}
          className="relative mx-auto w-full max-w-lg px-2 text-center sm:px-4"
        >
          <span
            className="pointer-events-none absolute -left-1 top-0 select-none font-serif text-[4.5rem] leading-none text-indigo-400/25 sm:-left-2 sm:text-[5.5rem]"
            aria-hidden
          >
            “
          </span>
          <p
            className="relative z-[1] font-serif text-[1.35rem] font-light italic leading-snug tracking-tight text-[#141210] sm:text-2xl md:text-[1.65rem] md:leading-[1.35]"
            style={{ fontFamily: "var(--serif)" }}
          >
            I Think. Therefore, I Am.
          </p>
          <footer className="relative z-[1] mt-5 border-t border-indigo-200/40 pt-4">
            <cite
              className="block font-mono text-[10px] font-medium uppercase not-italic tracking-[0.22em] text-[#64748b] sm:text-[11px]"
              style={{ fontFamily: "var(--mono)" }}
            >
              René Descartes
            </cite>
          </footer>
        </motion.blockquote>

        {backendBlocked && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="w-full max-w-lg rounded-xl border border-amber-200/80 bg-amber-50/90 px-4 py-4 text-left text-sm text-amber-950"
          >
            <p className="font-medium text-amber-900">Signed in with Google — API link missing</p>
            <p className="mt-2 leading-relaxed text-amber-900/85">
              The Next.js server could not exchange your Google session for app tokens. Start the API,
              set{" "}
              <code className="rounded bg-amber-100/90 px-1 py-0.5 font-mono text-[11px]">
                NEXT_PUBLIC_API_URL
              </code>{" "}
              to where the browser should call FastAPI, and if the web app runs in Docker set{" "}
              <code className="rounded bg-amber-100/90 px-1 py-0.5 font-mono text-[11px]">
                INTERNAL_API_URL
              </code>{" "}
              (e.g. <code className="font-mono text-[11px]">http://host.docker.internal:8000</code>)
              so the Next.js server can reach the API. Ensure API{" "}
              <code className="rounded bg-amber-100/90 px-1 py-0.5 font-mono text-[11px]">
                GOOGLE_CLIENT_ID
              </code>{" "}
              matches this app.
            </p>
            <p className="mt-2 font-mono text-[11px] text-amber-800/80">
              Browser API base: {publicApiBaseUrl()}
            </p>
            <p className="mt-3 text-xs text-amber-900/75">
              After the API is running with matching Google client config, sign out and use &quot;Sign in with
              Google&quot; again so the app can exchange your session.
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => void signOut({ callbackUrl: "/" })}
                className="rounded-lg bg-amber-900 px-4 py-2 text-xs font-medium text-white hover:bg-amber-950"
              >
                Sign out
              </button>
            </div>
          </motion.div>
        )}

        {/* Sign in button */}
        <motion.button
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={() => {
            void signIn("google", { callbackUrl: "/dashboard" });
          }}
          disabled={status === "loading" || backendBlocked}
          className="mt-2 flex h-12 items-center gap-3 rounded-full bg-[#111827] px-7 text-base font-medium text-white shadow-sm transition-colors hover:bg-[#1f2937] disabled:opacity-50"
        >
          <svg className="h-5 w-5" viewBox="0 0 24 24">
            <path
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"
              fill="#4285F4"
            />
            <path
              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              fill="#34A853"
            />
            <path
              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
              fill="#FBBC05"
            />
            <path
              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
              fill="#EA4335"
            />
          </svg>
          {status === "loading" ? "Connecting..." : "Sign in with Google"}
        </motion.button>

        {/* Features hint */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.7 }}
          className="mt-4 flex flex-wrap justify-center gap-5 text-sm text-[#4b5563]"
        >
          {[
            "Research Reports",
            "Chat",
            "Explore",
            "Learn",
          ].map((feature) => (
            <span key={feature} className="flex items-center gap-1.5">
              <span className="h-1 w-1 rounded-full bg-indigo-500" />
              {feature}
            </span>
          ))}
        </motion.div>
      </motion.div>
    </div>
  );
}

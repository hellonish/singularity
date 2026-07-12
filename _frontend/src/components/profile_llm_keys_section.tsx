"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useRef, useState } from "react";
import { Pencil, Trash2 } from "lucide-react";
import { usersApi } from "@/lib/api";
import {
  BYOK_PROVIDER_OPTIONS,
  BYOK_RECOMMENDED_MODELS,
} from "@/lib/byok_recommended_models";

function SectionHeader({ title }: { title: string }) {
  return (
    <h2
      style={{
        fontFamily: "var(--mono, 'JetBrains Mono', monospace)",
        fontSize: 12,
        letterSpacing: "0.08em",
        textTransform: "uppercase",
        color: "#4b5563",
        marginBottom: 16,
      }}
    >
      {title}
    </h2>
  );
}

function maskKey(lastFour: string) {
  return `••••••••…${lastFour}`;
}

/**
 * Purpose: Profile BYOK UI — one row to pick provider + paste key + Set; table of saved keys
 * with Edit/Delete; recommended models per provider that has a key.
 * Inputs: apiReady gates queries until the session has an access token.
 * Outputs: Renders form, credential list, and model hints aligned with the chat catalog.
 */
export function ProfileLlmKeysSection({ apiReady }: { apiReady: boolean }) {
  const queryClient = useQueryClient();
  const formRef = useRef<HTMLDivElement>(null);
  const secretInputRef = useRef<HTMLInputElement>(null);

  const [formProvider, setFormProvider] = useState(BYOK_PROVIDER_OPTIONS[0]?.id ?? "grok");
  const [formSecret, setFormSecret] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["llm-credentials"],
    queryFn: () => usersApi.llmCredentials(),
    enabled: apiReady,
  });

  const credentials = data?.credentials ?? [];
  const sortedCredentials = [...credentials].sort((a, b) =>
    a.provider.localeCompare(b.provider),
  );

  const saveMut = useMutation({
    mutationFn: ({ provider, secret }: { provider: string; secret: string }) =>
      usersApi.putLlmCredential(provider, secret),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["llm-credentials"] });
      void queryClient.invalidateQueries({ queryKey: ["llm-catalog"] });
      setFormSecret("");
    },
  });

  const delMut = useMutation({
    mutationFn: (provider: string) => usersApi.deleteLlmCredential(provider),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["llm-credentials"] });
      void queryClient.invalidateQueries({ queryKey: ["llm-catalog"] });
    },
  });

  const onSetKey = useCallback(() => {
    const s = formSecret.trim();
    if (s.length < 8) return;
    saveMut.mutate({ provider: formProvider, secret: s });
  }, [formProvider, formSecret, saveMut]);

  const onEdit = useCallback((provider: string) => {
    setFormProvider(provider);
    setFormSecret("");
    formRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    queueMicrotask(() => secretInputRef.current?.focus());
  }, []);

  const providerLabel = (id: string) =>
    BYOK_PROVIDER_OPTIONS.find((p) => p.id === id)?.label ?? id;

  const connectedProviders = new Set(credentials.map((c) => c.provider));

  return (
    <section>
      <SectionHeader title="LLM API keys (BYOK)" />
      <p className="mb-4 max-w-2xl text-sm leading-relaxed text-[#5c5952]">
        Keys are encrypted on the server. Chat and Research use the best models from the API keys you
        provide — add keys for any provider you want to use, and their models become available across
        both Chat and Research.
      </p>

      <div
        ref={formRef}
        className="mb-6 rounded-xl p-4"
        style={{ background: "#ffffff", border: "1px solid #e5e2db" }}
      >
        <p className="mb-3 text-xs font-medium uppercase tracking-wide text-[#6b7280]">
          Add or replace a key
        </p>
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={formProvider}
            onChange={(e) => setFormProvider(e.target.value)}
            className="min-w-[10.5rem] rounded-lg border border-[#e5e2db] bg-white px-3 py-2 text-sm text-[#111827] outline-none focus:border-[#6366f1]"
            aria-label="LLM provider"
          >
            {BYOK_PROVIDER_OPTIONS.map((p) => (
              <option key={p.id} value={p.id}>
                {p.label}
              </option>
            ))}
          </select>
          <input
            ref={secretInputRef}
            type="password"
            autoComplete="off"
            placeholder="API key"
            value={formSecret}
            onChange={(e) => setFormSecret(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") onSetKey();
            }}
            className="min-w-[12rem] flex-1 rounded-lg border border-[#e5e2db] bg-white px-3 py-2 text-sm text-[#111827] outline-none focus:border-[#6366f1]"
          />
          <button
            type="button"
            disabled={formSecret.trim().length < 8 || saveMut.isPending}
            onClick={onSetKey}
            className="shrink-0 rounded-lg bg-[#111827] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[#1f2937] disabled:opacity-40"
          >
            {saveMut.isPending ? "Saving…" : "Set key"}
          </button>
        </div>
        <p className="mt-2 text-xs text-[#6b7280]">
          Use <span className="font-mono text-[11px]">Edit</span> on a saved key to switch the
          provider above and paste a replacement.
        </p>
        {saveMut.isError ? (
          <p className="mt-2 text-xs text-red-600">
            {(saveMut.error as Error)?.message ?? "Could not save key"}
          </p>
        ) : null}
      </div>

      {isLoading ? (
        <div
          className="h-20 animate-pulse rounded-xl bg-white/80"
          style={{ border: "1px solid #e5e2db" }}
        />
      ) : sortedCredentials.length === 0 ? (
        <p className="text-sm text-[#6b7280]">No API keys saved yet.</p>
      ) : (
        <div
          className="overflow-x-auto rounded-xl"
          style={{ background: "#ffffff", border: "1px solid #e5e2db" }}
        >
          <table className="w-full min-w-[320px] text-left text-sm">
            <thead>
              <tr className="border-b border-[#e5e2db]">
                <th className="px-4 py-3 font-mono text-[11px] font-medium uppercase tracking-wide text-[#6b7280]">
                  Provider
                </th>
                <th className="px-4 py-3 font-mono text-[11px] font-medium uppercase tracking-wide text-[#6b7280]">
                  API key
                </th>
                <th className="px-4 py-3 font-mono text-[11px] font-medium uppercase tracking-wide text-[#6b7280]">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {sortedCredentials.map((row) => (
                <tr key={row.id} className="border-b border-[#e5e2db] last:border-0">
                  <td className="px-4 py-3 font-medium text-[#111827]">
                    {providerLabel(row.provider)}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-[#374151]">
                    {maskKey(row.last_four)}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <button
                        type="button"
                        onClick={() => onEdit(row.provider)}
                        className="inline-flex items-center gap-1 rounded-lg border border-[#e5e2db] bg-white px-2.5 py-1.5 text-xs font-medium text-[#374151] transition-colors hover:bg-[#f9faf8]"
                      >
                        <Pencil size={14} strokeWidth={1.75} aria-hidden />
                        Edit
                      </button>
                      <button
                        type="button"
                        disabled={delMut.isPending}
                        onClick={() => delMut.mutate(row.provider)}
                        className="inline-flex items-center gap-1 rounded-lg border border-red-200 bg-white px-2.5 py-1.5 text-xs font-medium text-red-700 transition-colors hover:bg-red-50 disabled:opacity-40"
                      >
                        <Trash2 size={14} strokeWidth={1.75} aria-hidden />
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {connectedProviders.size > 0 ? (
        <div className="mt-8">
          <SectionHeader title="Popular models for your keys" />
          <p className="mb-4 max-w-2xl text-sm leading-relaxed text-[#5c5952]">
            These are suggested models available from your connected providers. Select any of them in
            the Chat <span className="font-mono text-xs">Model</span> dropdown or use them with Research.
            Model IDs match each provider&apos;s live catalog.
          </p>
          <div className="space-y-6">
            {BYOK_PROVIDER_OPTIONS.filter((p) => connectedProviders.has(p.id)).map((p) => {
              const models = BYOK_RECOMMENDED_MODELS[p.id] ?? [];
              if (models.length === 0) return null;
              return (
                <div key={p.id}>
                  <h3 className="mb-3 font-mono text-xs font-medium uppercase tracking-wide text-[#4b5563]">
                    {p.label}
                  </h3>
                  <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                    {models.map((m) => (
                      <div
                        key={m.model_id}
                        className="rounded-xl p-4"
                        style={{ background: "#ffffff", border: "1px solid #e5e2db" }}
                      >
                        <p className="font-medium text-[#111827]">{m.label}</p>
                        <p className="mt-1 text-xs leading-relaxed text-[#5c5952]">{m.note}</p>
                        <p className="mt-2 font-mono text-[10px] text-[#9ca3af] break-all">
                          {m.model_id}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : null}

      {delMut.isError ? (
        <p className="mt-3 text-xs text-red-600">
          {(delMut.error as Error)?.message ?? "Could not remove API key"}
        </p>
      ) : null}
    </section>
  );
}

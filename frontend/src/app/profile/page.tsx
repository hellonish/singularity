"use client";

import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { usersApi } from "@/lib/api";
import { UserMenu } from "@/components/user-menu";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, BarChart, Bar,
} from "recharts";

const CHART_COLORS = ["#6366f1", "#a855f7", "#ec4899", "#f59e0b", "#10b981", "#3b82f6", "#ef4444"];
type ChartTooltipPoint = { name: string; value: number; color: string };
type ModelBreakdownItem = { model: string; pct: number };
type DeviceOsItem = { os: string; count: number };

function StatCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div
      className="rounded-xl p-5"
      style={{ background: "#ffffff", border: "1px solid #e5e2db" }}
    >
      <p style={{ fontFamily: "var(--mono, 'JetBrains Mono', monospace)", fontSize: 11, letterSpacing: "0.08em", textTransform: "uppercase", color: "#4b5563", marginBottom: 8 }}>
        {label}
      </p>
      <p style={{ fontSize: 28, fontWeight: 600, color: "#1a1a1a", lineHeight: 1 }}>{value}</p>
      {sub && <p style={{ fontFamily: "var(--mono, 'JetBrains Mono', monospace)", fontSize: 11, color: "#9ca3af", marginTop: 4 }}>{sub}</p>}
    </div>
  );
}

function SectionHeader({ title }: { title: string }) {
  return (
    <h2 style={{ fontFamily: "var(--mono, 'JetBrains Mono', monospace)", fontSize: 12, letterSpacing: "0.08em", textTransform: "uppercase", color: "#4b5563", marginBottom: 16 }}>
      {title}
    </h2>
  );
}

function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}k`;
  return String(n);
}

/** API may send Decimal-derived fields as strings in JSON. */
function coerceUsd(value: unknown): number {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

const CustomTooltip = ({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: ChartTooltipPoint[];
  label?: string;
}) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background: "#ffffff", border: "1px solid #e5e2db", borderRadius: 8, padding: "8px 12px" }}>
      <p style={{ fontFamily: "var(--mono, monospace)", fontSize: 11, color: "#6b7280", marginBottom: 4 }}>{label}</p>
      {payload.map((p) => (
        <p key={p.name} style={{ fontFamily: "var(--mono, monospace)", fontSize: 12, color: p.color }}>
          {p.name}: {p.name === "cost_usd" ? `$${Number(p.value).toFixed(3)}` : formatTokens(p.value)}
        </p>
      ))}
    </div>
  );
};

export default function ProfilePage() {
  const { status: authStatus } = useSession();
  const router = useRouter();
  const [range, setRange] = useState<"7d" | "30d" | "90d">("30d");

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ["user-stats"],
    queryFn: () => usersApi.stats(),
    enabled: authStatus === "authenticated",
  });

  const { data: usageData } = useQuery({
    queryKey: ["user-usage", range],
    queryFn: () => usersApi.usage(range),
    enabled: authStatus === "authenticated",
  });

  const { data: modelsData } = useQuery({
    queryKey: ["user-models"],
    queryFn: () => usersApi.models(),
    enabled: authStatus === "authenticated",
  });

  const { data: devicesData } = useQuery({
    queryKey: ["user-devices"],
    queryFn: () => usersApi.devices(),
    enabled: authStatus === "authenticated",
  });

  if (authStatus === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center" style={{ background: "#f9fafb" }}>
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-[#6366f1] border-t-transparent" />
      </div>
    );
  }

  if (authStatus === "unauthenticated") { router.push("/"); return null; }

  const modelBreakdown = (modelsData?.breakdown ?? []) as ModelBreakdownItem[];
  const deviceOs = (devicesData?.os ?? []) as DeviceOsItem[];

  return (
    <div className="min-h-screen" style={{ background: "#f8fafc" }}>
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 bg-white" style={{ borderBottom: "1px solid #e5e2db" }}>
        <div className="flex items-center gap-4">
          <button
            onClick={() => router.push("/dashboard")}
            style={{ fontFamily: "var(--mono, monospace)", fontSize: 12, color: "#6b7280", display: "flex", alignItems: "center", gap: 6 }}
          >
            &larr; Dashboard
          </button>
          <h1 style={{ fontFamily: "var(--mono, monospace)", fontSize: 13, color: "#1a1a1a" }}>
            Usage &amp; Stats
          </h1>
        </div>
        <UserMenu />
      </header>

      <main className="mx-auto w-full max-w-7xl px-6 py-8 space-y-10">

        {/* Stats grid */}
        <section>
          <SectionHeader title="Overview" />
          {statsLoading ? (
            <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
              {[...Array(6)].map((_, i) => (
                <div key={i} className="h-24 rounded-xl animate-pulse" style={{ background: "#ffffff" }} />
              ))}
            </div>
          ) : stats ? (
            <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
              <StatCard label="Total Reports" value={stats.total_reports} />
              <StatCard label="Total Tokens" value={formatTokens(stats.total_tokens)} />
              <StatCard
                label="Total Cost"
                value={`$${coerceUsd(stats.total_cost_usd).toFixed(2)}`}
              />
              <StatCard label="This Week" value={stats.reports_this_week} sub="reports" />
              <StatCard label="Tokens Today" value={formatTokens(stats.tokens_today)} sub={`${formatTokens(stats.tokens_remaining_today)} remaining`} />
              <StatCard label="Streak" value={`${stats.streak_days}d`} sub={stats.favorite_model ? `fav: ${stats.favorite_model}` : undefined} />
            </div>
          ) : null}
        </section>

        {/* Token usage timeline */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <SectionHeader title="Token Usage" />
            <div className="flex gap-1">
              {(["7d", "30d", "90d"] as const).map((r) => (
                <button
                  key={r}
                  onClick={() => setRange(r)}
                  style={{
                    fontFamily: "var(--mono, monospace)",
                    fontSize: 12,
                    padding: "3px 10px",
                    borderRadius: 6,
                    border: `1px solid ${range === r ? "#6366f1" : "#e5e2db"}`,
                    background: range === r ? "rgba(99,102,241,0.1)" : "transparent",
                    color: range === r ? "#4338ca" : "#4b5563",
                    cursor: "pointer",
                  }}
                >
                  {r}
                </button>
              ))}
            </div>
          </div>
          <div className="rounded-xl p-5" style={{ background: "#ffffff", border: "1px solid #e5e2db", height: 220 }}>
            {usageData?.series?.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={usageData.series} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e2db" />
                  <XAxis dataKey="date" tick={{ fontFamily: "var(--mono, monospace)", fontSize: 10, fill: "#6b7280" }} tickFormatter={(v) => v.slice(5)} />
                  <YAxis tick={{ fontFamily: "var(--mono, monospace)", fontSize: 10, fill: "#6b7280" }} tickFormatter={formatTokens} />
                  <Tooltip content={<CustomTooltip />} />
                  <Line type="monotone" dataKey="tokens" stroke="#6366f1" strokeWidth={2} dot={false} name="tokens" />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center">
                <p style={{ fontFamily: "var(--mono, monospace)", fontSize: 11, color: "#9ca3af" }}>No data for this period</p>
              </div>
            )}
          </div>
        </section>

        {/* Model breakdown + device breakdown side by side */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Model breakdown */}
          <section>
            <SectionHeader title="Models Used" />
            <div className="rounded-xl p-5" style={{ background: "#ffffff", border: "1px solid #e5e2db", height: 220 }}>
              {modelBreakdown.length ? (
                <div className="flex items-center gap-4 h-full">
                  <ResponsiveContainer width={160} height="100%">
                    <PieChart>
                      <Pie data={modelBreakdown} dataKey="pct" cx="50%" cy="50%" innerRadius={45} outerRadius={70} paddingAngle={3}>
                        {modelBreakdown.map((_, i: number) => (
                          <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                        ))}
                      </Pie>
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="flex-1 space-y-2 overflow-y-auto" style={{ maxHeight: 180 }}>
                    {modelBreakdown.map((item, i: number) => (
                      <div key={item.model} className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <div style={{ width: 8, height: 8, borderRadius: "50%", background: CHART_COLORS[i % CHART_COLORS.length], flexShrink: 0 }} />
                          <span style={{ fontFamily: "var(--mono, monospace)", fontSize: 11, color: "#1a1a1a" }}>{item.model}</span>
                        </div>
                        <span style={{ fontFamily: "var(--mono, monospace)", fontSize: 11, color: "#6b7280" }}>{item.pct}%</span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="flex h-full items-center justify-center">
                  <p style={{ fontFamily: "var(--mono, monospace)", fontSize: 11, color: "#9ca3af" }}>No model data yet</p>
                </div>
              )}
            </div>
          </section>

          {/* Device/OS breakdown */}
          <section>
            <SectionHeader title="Devices & OS" />
            <div className="rounded-xl p-5" style={{ background: "#ffffff", border: "1px solid #e5e2db", height: 220 }}>
              {deviceOs.length ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={deviceOs} layout="vertical" margin={{ top: 0, right: 10, left: 0, bottom: 0 }}>
                    <XAxis type="number" tick={{ fontFamily: "var(--mono, monospace)", fontSize: 10, fill: "#6b7280" }} />
                    <YAxis type="category" dataKey="os" width={80} tick={{ fontFamily: "var(--mono, monospace)", fontSize: 10, fill: "#6b7280" }} />
                    <Tooltip
                      contentStyle={{ background: "#ffffff", border: "1px solid #e5e2db", borderRadius: 8, fontFamily: "var(--mono, monospace)", fontSize: 11 }}
                      labelStyle={{ color: "#1a1a1a" }}
                      itemStyle={{ color: "#6366f1" }}
                    />
                    <Bar dataKey="count" fill="#6366f1" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex h-full items-center justify-center">
                  <p style={{ fontFamily: "var(--mono, monospace)", fontSize: 11, color: "#9ca3af" }}>No device data yet</p>
                </div>
              )}
            </div>
          </section>
        </div>

        {/* Cost timeline */}
        <section>
          <SectionHeader title="Cost (USD)" />
          <div className="rounded-xl p-5" style={{ background: "#ffffff", border: "1px solid #e5e2db", height: 180 }}>
            {usageData?.series?.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={usageData.series} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e2db" />
                  <XAxis dataKey="date" tick={{ fontFamily: "var(--mono, monospace)", fontSize: 10, fill: "#6b7280" }} tickFormatter={(v) => v.slice(5)} />
                  <YAxis
                    tick={{ fontFamily: "var(--mono, monospace)", fontSize: 10, fill: "#6b7280" }}
                    tickFormatter={(v) => `$${coerceUsd(v).toFixed(2)}`}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Line type="monotone" dataKey="cost_usd" stroke="#10b981" strokeWidth={2} dot={false} name="cost_usd" />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center">
                <p style={{ fontFamily: "var(--mono, monospace)", fontSize: 11, color: "#9ca3af" }}>No cost data yet</p>
              </div>
            )}
          </div>
        </section>

      </main>
    </div>
  );
}

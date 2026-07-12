import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(date: string | Date): string {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(date));
}

/**
 * Relative time from now for list UI (e.g. report cards).
 *
 * Uses elapsed milliseconds; anything under one full minute shows as "Just now"
 * so we never display misleading "0m ago" (floor(ms/60000) is 0 for 0–59s).
 */
export function formatRelative(date: string | Date): string {
  const d = new Date(date);
  const diffMs = Date.now() - d.getTime();
  if (!Number.isFinite(diffMs)) return formatDate(d);
  if (diffMs < 0) return "Just now";
  const secs = Math.floor(diffMs / 1000);
  if (secs < 60) return "Just now";
  const mins = Math.floor(diffMs / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  const weeks = Math.floor(days / 7);
  if (weeks < 4) return `${weeks}w ago`;
  return formatDate(d);
}

export function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  return n.toString();
}

/** Collapses whitespace and truncates for compact pane / pill labels. */
export function truncateDisplayLabel(text: string, maxLen = 32): string {
  const single = text.replace(/\s+/g, " ").trim();
  if (!single) return "";
  if (single.length <= maxLen) return single;
  return `${single.slice(0, Math.max(1, maxLen - 1))}…`;
}

/** Backend research intensity: 1 = low, 2 = medium, 3 = high. */
export type ResearchIntensityTier = 1 | 2 | 3;

export const RESEARCH_INTENSITY_OPTIONS: readonly {
  tier: ResearchIntensityTier;
  label: string;
}[] = [
  { tier: 1, label: "Low" },
  { tier: 2, label: "Medium" },
  { tier: 3, label: "High" },
];

export function researchIntensityLabel(tier: number): string {
  if (tier === 1) return "Low";
  if (tier === 3) return "High";
  return "Medium";
}

export function clampResearchIntensityTier(n: number): ResearchIntensityTier {
  if (n <= 1) return 1;
  if (n >= 3) return 3;
  return 2;
}

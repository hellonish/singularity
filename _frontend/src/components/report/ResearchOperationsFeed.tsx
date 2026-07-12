"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import {
  formatStoryboardElapsed,
  presentResearchActivity,
  type RawResearchActivity,
  type PresentedResearchActivity,
} from "@/lib/research_activity_presenter";

const PHASE_CHIP: Record<string, { bg: string; border: string; color: string }> = {
  planning: {
    bg: "rgba(99,102,241,0.08)",
    border: "rgba(99,102,241,0.25)",
    color: "#4338ca",
  },
  retrieval: {
    bg: "rgba(6,182,212,0.08)",
    border: "rgba(6,182,212,0.28)",
    color: "#0e7490",
  },
  writing: {
    bg: "rgba(245,158,11,0.1)",
    border: "rgba(245,158,11,0.35)",
    color: "#b45309",
  },
  polish: {
    bg: "rgba(139,92,246,0.09)",
    border: "rgba(139,92,246,0.28)",
    color: "#6d28d9",
  },
};

function phaseStyle(phase: string) {
  return PHASE_CHIP[phase] ?? {
    bg: "var(--rpt-bg3)",
    border: "var(--rpt-border-hi)",
    color: "var(--rpt-text-dim)",
  };
}

function StoryCard({ item }: { item: PresentedResearchActivity }) {
  const ps = phaseStyle(item.phase);
  const isMajor = item.weight === "major";
  const isAmbient = item.weight === "ambient";

  return (
    <div
      style={{
        borderRadius: 10,
        border: `1px solid ${isMajor ? "var(--rpt-border-hi)" : "rgba(0,0,0,0.06)"}`,
        background: isMajor ? "rgba(255,255,255,0.92)" : "rgba(255,255,255,0.72)",
        padding: isMajor ? "14px 16px" : isAmbient ? "8px 12px" : "10px 14px",
        boxShadow: isMajor ? "0 1px 12px rgba(0,0,0,0.04)" : "none",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "baseline",
          gap: 10,
          marginBottom: 6,
          flexWrap: "wrap",
        }}
      >
        <span
          style={{
            fontFamily: "var(--mono)",
            fontSize: 10,
            color: "var(--rpt-text-dim)",
            letterSpacing: "0.04em",
          }}
        >
          {formatStoryboardElapsed(item.elapsedMs)}
        </span>
        <span
          style={{
            fontFamily: "var(--mono)",
            fontSize: 9,
            textTransform: "uppercase",
            letterSpacing: "0.06em",
            padding: "2px 8px",
            borderRadius: 999,
            background: ps.bg,
            border: `1px solid ${ps.border}`,
            color: ps.color,
          }}
        >
          {item.phase}
        </span>
      </div>
      <div
        style={{
          fontFamily: "'Newsreader', Georgia, serif",
          fontSize: isMajor ? 17 : isAmbient ? 14 : 15,
          fontWeight: 400,
          color: "var(--rpt-text)",
          lineHeight: 1.35,
          marginBottom: 6,
        }}
      >
        {item.headline}
      </div>
      <div
        style={{
          fontFamily: "var(--mono)",
          fontSize: 11,
          color: "var(--rpt-text-dim)",
          lineHeight: 1.45,
          display: "-webkit-box",
          WebkitLineClamp: isAmbient ? 2 : 3,
          WebkitBoxOrient: "vertical" as const,
          overflow: "hidden",
        }}
      >
        {item.subtext}
      </div>
      {item.chips.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 10 }}>
          {item.chips.map((c) => (
            <span
              key={c}
              style={{
                fontFamily: "var(--mono)",
                fontSize: 10,
                color: "#4b5563",
                background: "#f3f4f6",
                border: "1px solid #e5e7eb",
                borderRadius: 6,
                padding: "3px 8px",
              }}
            >
              {c}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

const MAX_ACTIVITY = 200;

export interface ResearchOperationsFeedProps {
  rawEntries: RawResearchActivity[];
  isRunning: boolean;
}

/**
 * Scrollable Research Storyboard: presents pipeline activity as editorial moments
 * with optional live follow-scroll while the job runs.
 */
export function ResearchOperationsFeed({ rawEntries, isRunning }: ResearchOperationsFeedProps) {
  const scrollerRef = useRef<HTMLDivElement>(null);
  const [stickToBottom, setStickToBottom] = useState(true);

  const presented = rawEntries.map((e) => presentResearchActivity(e));

  const onScroll = useCallback(() => {
    const el = scrollerRef.current;
    if (!el) return;
    const threshold = 80;
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < threshold;
    setStickToBottom(nearBottom);
  }, []);

  useEffect(() => {
    const el = scrollerRef.current;
    if (!el || !stickToBottom || !isRunning) return;
    el.scrollTop = el.scrollHeight;
  }, [rawEntries.length, stickToBottom, isRunning]);

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        minHeight: 280,
        maxHeight: "min(70vh, 560px)",
        borderRadius: 12,
        border: "1px solid var(--rpt-border-hi)",
        background: "linear-gradient(180deg, rgba(255,255,255,0.98) 0%, rgba(250,250,249,0.95) 100%)",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          padding: "12px 16px",
          borderBottom: "1px solid var(--rpt-border-hi)",
          fontFamily: "var(--mono)",
          fontSize: 10,
          letterSpacing: "0.12em",
          textTransform: "uppercase",
          color: "var(--rpt-text-dim)",
        }}
      >
        Research Storyboard
      </div>
      <div
        ref={scrollerRef}
        onScroll={onScroll}
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "16px 14px 20px",
          position: "relative",
        }}
      >
        {presented.length === 0 ? (
          <div
            style={{
              fontFamily: "var(--mono)",
              fontSize: 12,
              color: "var(--rpt-text-dim)",
              textAlign: "center",
              padding: "48px 16px",
              animation: "pulse 2s ease-in-out infinite",
            }}
          >
            Waiting for orchestrator…
          </div>
        ) : (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: 12,
              borderLeft: "2px solid var(--rpt-border-hi)",
              paddingLeft: 16,
              marginLeft: 4,
            }}
          >
            {presented.map((item) => (
              <StoryCard key={item.id} item={item} />
            ))}
          </div>
        )}
      </div>
      {rawEntries.length >= MAX_ACTIVITY && (
        <div
          style={{
            fontFamily: "var(--mono)",
            fontSize: 10,
            color: "var(--rpt-text-dim)",
            padding: "6px 14px 10px",
            borderTop: "1px solid var(--rpt-border-hi)",
          }}
        >
          Showing latest {MAX_ACTIVITY} moments (older entries trimmed in this session).
        </div>
      )}
    </div>
  );
}

export const RESEARCH_ACTIVITY_CAP = MAX_ACTIVITY;

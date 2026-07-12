/**
 * Maps structured backend `job_activity` events to premium, reader-facing copy.
 * Backend stays factual (`kind` + `meta`); this module owns tone and layout hints.
 */

export interface RawResearchActivity {
  id: string;
  kind: string;
  phase: string;
  meta?: Record<string, unknown>;
  elapsed_ms?: number;
}

export type StoryMomentWeight = "major" | "supporting" | "ambient";

export interface PresentedResearchActivity {
  id: string;
  kind: string;
  phase: string;
  weight: StoryMomentWeight;
  headline: string;
  subtext: string;
  chips: string[];
  elapsedMs: number;
}

function num(v: unknown): number {
  return typeof v === "number" && !Number.isNaN(v) ? v : 0;
}

function str(v: unknown): string {
  return typeof v === "string" ? v : "";
}

function majorKinds(): Set<string> {
  return new Set([
    "pipeline_start",
    "managers_spawn",
    "lead_started",
    "lead_finished",
    "retrieval_plan_ready",
    "polish_started",
    "polish_finished",
  ]);
}

function ambientKinds(): Set<string> {
  return new Set(["manager_started", "retrieval_skill_started", "writer_jit_search"]);
}

function momentWeight(kind: string): StoryMomentWeight {
  if (majorKinds().has(kind)) return "major";
  if (ambientKinds().has(kind)) return "ambient";
  return "supporting";
}

/** Renders elapsed since job start (from worker), e.g. +1m 04s */
export function formatStoryboardElapsed(ms: number): string {
  if (ms <= 0) return "+0s";
  const s = Math.floor(ms / 1000);
  const m = Math.floor(s / 60);
  const rs = s % 60;
  if (m <= 0) return `+${rs}s`;
  if (m < 60) {
    return `+${m}m ${rs.toString().padStart(2, "0")}s`;
  }
  const h = Math.floor(m / 60);
  const rm = m % 60;
  return `+${h}h ${rm}m`;
}

/** One-line context under the phase rail */
export function phaseStoryboardContext(phase: string | null): string {
  switch (phase) {
    case "planning":
      return "Multiple planning paths are being explored";
    case "retrieval":
      return "Evidence is being gathered and compared";
    case "writing":
      return "The draft is taking shape";
    case "polish":
      return "The final pass is underway";
    default:
      return "Preparing your research run…";
  }
}

function rationaleSnippet(raw: unknown, max = 160): string {
  const t = str(raw).trim();
  if (!t) return "One planning path refined how the report should unfold.";
  const cut = t.length > max ? `${t.slice(0, max).trim()}…` : t;
  return cut;
}

/**
 * Inputs:
 * - evt: one normalized activity row (stable `id`, `kind`, `phase`, optional `meta`, `elapsed_ms`).
 * Outputs:
 * - PresentedResearchActivity with headline, subtext, chips, and visual weight for the storyboard.
 */
export function presentResearchActivity(evt: RawResearchActivity): PresentedResearchActivity {
  const meta = evt.meta ?? {};
  const chips: string[] = [];
  const mockChip = () => {
    if (meta.mock === true) chips.push("Mock");
  };

  let headline = "Update";
  let subtext = "The research pipeline advanced.";

  switch (evt.kind) {
    case "pipeline_start":
      headline = "Research is underway";
      subtext = "Setting up the report workflow and preparing the first pass.";
      if (typeof meta.strength === "number") {
        const tier =
          meta.strength === 1
            ? "Low"
            : meta.strength === 3
              ? "High"
              : "Medium";
        chips.push(`Intensity: ${tier}`);
      }
      mockChip();
      break;
    case "domain_classified":
      headline = "Finding the right frame";
      subtext =
        "The system is identifying the domain so the report structure fits the topic.";
      if (str(meta.label)) chips.push(str(meta.label));
      if (str(meta.confidence)) chips.push(String(meta.confidence));
      mockChip();
      break;
    case "managers_spawn":
      headline = "Exploring multiple angles";
      subtext = "Three planning threads are shaping different ways to approach the report.";
      chips.push("3 planners");
      mockChip();
      break;
    case "manager_started": {
      headline = "Developing a candidate outline";
      subtext = "One planning path is working through scope, ordering, and emphasis.";
      const perspective = str(meta.perspective);
      if (perspective) chips.push(perspective);
      mockChip();
      break;
    }
    case "manager_finished": {
      headline = "A new structure is on the table";
      subtext = rationaleSnippet(meta.rationale);
      const nc = num(meta.node_count);
      if (nc > 0) chips.push(`${nc} sections`);
      const perspective = str(meta.perspective);
      if (perspective) chips.push(perspective);
      mockChip();
      break;
    }
    case "lead_started":
      headline = "Choosing the strongest direction";
      subtext = "The lead planner is comparing proposals and building a final structure.";
      chips.push("Lead planner");
      mockChip();
      break;
    case "lead_finished":
      headline = "The report structure is locked";
      subtext = "The strongest ideas have been merged into a single plan.";
      if (num(meta.max_depth) > 0) chips.push(`depth ${num(meta.max_depth)}`);
      if (num(meta.total_nodes) > 0) chips.push(`${num(meta.total_nodes)} sections`);
      mockChip();
      break;
    case "cache_hit":
      headline = "Reusing trusted groundwork";
      subtext =
        "Relevant source material was already available, so the system can move faster.";
      chips.push("Cache hit");
      mockChip();
      break;
    case "cache_miss":
      headline = "Building the source base";
      subtext = "Fresh evidence is being gathered for this report.";
      chips.push("Fresh run");
      mockChip();
      break;
    case "retrieval_plan_ready": {
      headline = "Choosing how to investigate";
      subtext = "The system selected the best research methods for this question.";
      const skills = meta.skills;
      if (Array.isArray(skills)) chips.push(`${skills.length} methods`);
      mockChip();
      break;
    }
    case "retrieval_skill_started": {
      headline = "Pulling in evidence";
      subtext = "A research method is now scanning for high-value material.";
      const skill = str(meta.skill);
      if (skill) chips.push(skill);
      const qc = num(meta.query_count);
      if (qc > 0) chips.push(`${qc} queries`);
      mockChip();
      break;
    }
    case "retrieval_skill_finished": {
      headline = "New evidence added";
      subtext = "This pass expanded the source base for the report.";
      const skill = str(meta.skill);
      if (skill) chips.push(skill);
      const sf = num(meta.sources_found);
      const cs = num(meta.chunks_stored);
      if (sf > 0) chips.push(`${sf} sources`);
      if (cs > 0) chips.push(`${cs} evidence chunks`);
      mockChip();
      break;
    }
    case "coverage_audit":
      headline = "Checking for weak spots";
      subtext = "The system is looking for sections that still need stronger evidence.";
      if (meta.threshold_met === true) chips.push("Coverage solid");
      else {
        const starved = num(meta.starved_count);
        if (starved > 0) chips.push(`${starved} gaps`);
      }
      mockChip();
      break;
    case "writers_depth":
      headline = "Drafting the report body";
      subtext =
        "Multiple writing agents are working through one layer of the report in parallel.";
      if (num(meta.node_count) > 0) chips.push(`${num(meta.node_count)} writers`);
      if (typeof meta.depth === "number") chips.push(`depth ${meta.depth}`);
      mockChip();
      break;
    case "writer_jit_search":
      headline = "Refreshing a live section";
      subtext = "This part of the report needs current information before it is written.";
      chips.push("Live update");
      {
        const title = str(meta.section_title);
        if (title) chips.push(title.length > 40 ? `${title.slice(0, 40)}…` : title);
      }
      mockChip();
      break;
    case "polish_started":
      headline = "Refining the final read";
      subtext = "The draft is being tightened for clarity, flow, and presentation.";
      if (num(meta.section_count) > 0) chips.push(`${num(meta.section_count)} sections`);
      mockChip();
      break;
    case "polish_finished":
      headline = "Final polish complete";
      subtext = "The report is ready to render.";
      if (num(meta.char_count) > 0) {
        chips.push(`${num(meta.char_count).toLocaleString()} chars`);
      }
      mockChip();
      break;
    default:
      headline = evt.kind.replace(/_/g, " ");
      subtext = "Pipeline activity";
      mockChip();
  }

  return {
    id: evt.id,
    kind: evt.kind,
    phase: evt.phase,
    weight: momentWeight(evt.kind),
    headline,
    subtext,
    chips,
    elapsedMs: typeof evt.elapsed_ms === "number" ? evt.elapsed_ms : 0,
  };
}

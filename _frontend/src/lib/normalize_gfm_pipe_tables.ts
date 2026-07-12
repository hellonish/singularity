/**
 * Inserts missing GFM table separator rows so remark-gfm parses pipe tables.
 *
 * Models often emit:
 *   | A | B |
 *   | 1 | 2 |
 * without `|---|---|`; that parses as a single paragraph, not a table.
 * Code fences (```) are left unchanged.
 */

const FENCE_RE = /(```[\s\S]*?```)/g;

function isPipeTableRow(line: string): boolean {
  const t = line.trim();
  if (!t) return false;
  const pipes = t.match(/\|/g);
  return pipes !== null && pipes.length >= 2;
}

function isGfmSeparatorRow(line: string): boolean {
  const t = line.trim();
  if (!t || !t.includes("|")) return false;
  if (!/^[\s|:\-]+$/.test(t)) return false;
  return /-/.test(t);
}

function cellCountFromPipeRow(line: string): number {
  const t = line.trim();
  const parts = t.split("|").map((s) => s.trim()).filter((s) => s.length > 0);
  return Math.max(parts.length, 1);
}

function separatorLineForColumns(n: number): string {
  return `|${Array(n).fill(" --- ").join("|")}|`;
}

function insertSeparatorsInChunk(chunk: string): string {
  const lines = chunk.split("\n");
  const out: string[] = [];
  let i = 0;
  while (i < lines.length) {
    if (!isPipeTableRow(lines[i])) {
      out.push(lines[i]);
      i += 1;
      continue;
    }
    const start = i;
    while (i < lines.length && isPipeTableRow(lines[i])) {
      i += 1;
    }
    const block = lines.slice(start, i);
    if (block.length === 0) {
      continue;
    }
    if (block.length >= 2 && isGfmSeparatorRow(block[1])) {
      out.push(...block);
      continue;
    }
    const n = cellCountFromPipeRow(block[0]);
    const sep = separatorLineForColumns(n);
    out.push(block[0], sep, ...block.slice(1));
  }
  return out.join("\n");
}

/**
 * Ensures consecutive pipe rows have a GFM delimiter after the header row when missing.
 */
export function normalizeGfmPipeTables(markdown: string): string {
  const parts = markdown.split(FENCE_RE);
  return parts
    .map((segment, idx) =>
      idx % 2 === 1 ? segment : insertSeparatorsInChunk(segment),
    )
    .join("");
}

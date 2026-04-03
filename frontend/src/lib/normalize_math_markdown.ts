/**
 * Normalizes math-heavy markdown so remark-math / rehype-katex can render it.
 *
 * Models often emit LaTeX in parentheses "(a^2 + b^2 = c^2)" or TeX delimiters
 * "\\( ... \\)" / "\\[ ... \\]" instead of dollar signs. remark-math only
 * understands $...$ and $$...$$ by default.
 */

const FENCE_RE = /(```[\s\S]*?```)/g;

function replaceEscapedDisplayBrackets(chunk: string): string {
  const open = "\\[";
  const close = "\\]";
  let out = "";
  let i = 0;
  while (i < chunk.length) {
    const j = chunk.indexOf(open, i);
    if (j === -1) {
      out += chunk.slice(i);
      break;
    }
    out += chunk.slice(i, j);
    const k = chunk.indexOf(close, j + open.length);
    if (k === -1) {
      out += chunk.slice(j);
      break;
    }
    const inner = chunk.slice(j + open.length, k).trim();
    out += `\n$$\n${inner}\n$$\n`;
    i = k + close.length;
  }
  return out;
}

function replaceEscapedInlineParens(chunk: string): string {
  const open = "\\(";
  const close = "\\)";
  let out = "";
  let i = 0;
  while (i < chunk.length) {
    const j = chunk.indexOf(open, i);
    if (j === -1) {
      out += chunk.slice(i);
      break;
    }
    out += chunk.slice(i, j);
    const k = chunk.indexOf(close, j + open.length);
    if (k === -1) {
      out += chunk.slice(j);
      break;
    }
    const inner = chunk.slice(j + open.length, k).trim();
    out += `$${inner}$`;
    i = k + close.length;
  }
  return out;
}

function isLikelyInlineMathInner(inner: string): boolean {
  const s = inner.trim();
  if (s.length < 1 || s.length > 900) return false;
  if (s.includes("$")) return false;
  if (/^https?:\/\//i.test(s)) return false;
  if (/^mailto:/i.test(s)) return false;
  if (/\\(text|frac|sqrt|sum|int|alpha|beta|gamma|delta|theta|pi|infty|times|div|cdot|leq|geq|neq|pm|mp)\b/i.test(s)) {
    return true;
  }
  if (/[\^_]/.test(s)) return true;
  if (/=[^=]/.test(s) && /[a-zA-Z]/.test(s)) return true;
  if (/^[a-zA-Z]\s*[-+*/^]/.test(s) || /[-+*/^]\s*[a-zA-Z]/.test(s)) return true;
  if (/\d/.test(s) && /[a-zA-Z]/.test(s) && /[-+*/^=]/.test(s)) return true;
  return false;
}

function findMatchingParen(s: string, openIdx: number): number {
  let depth = 1;
  for (let i = openIdx + 1; i < s.length; i++) {
    const c = s[i];
    if (c === "\\") {
      i++;
      continue;
    }
    if (c === "(") depth++;
    else if (c === ")") {
      depth--;
      if (depth === 0) return i;
    }
  }
  return -1;
}

function replaceParenWrappedMath(chunk: string): string {
  let out = "";
  let i = 0;
  while (i < chunk.length) {
    if (chunk[i] !== "(") {
      out += chunk[i];
      i++;
      continue;
    }
    if (i > 0 && (chunk[i - 1] === "]" || chunk[i - 1] === "!")) {
      out += chunk[i];
      i++;
      continue;
    }
    const end = findMatchingParen(chunk, i);
    if (end === -1) {
      out += chunk[i];
      i++;
      continue;
    }
    const inner = chunk.slice(i + 1, end);
    if (isLikelyInlineMathInner(inner)) {
      out += `$${inner.trim()}$`;
      i = end + 1;
    } else {
      out += chunk[i];
      i++;
    }
  }
  return out;
}

function transformMathChunk(chunk: string): string {
  let s = chunk;
  s = replaceEscapedDisplayBrackets(s);
  s = replaceEscapedInlineParens(s);
  s = replaceParenWrappedMath(s);
  return s;
}

/**
 * Rewrites LLM-style math delimiters to remark-math dollar syntax.
 * Code fences (``` ... ```) are left unchanged.
 */
export function normalizeMathMarkdown(source: string): string {
  const parts = source.split(FENCE_RE);
  return parts
    .map((segment, idx) => (idx % 2 === 1 ? segment : transformMathChunk(segment)))
    .join("");
}

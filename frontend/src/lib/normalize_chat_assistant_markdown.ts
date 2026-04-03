import { normalizeGfmPipeTables } from "@/lib/normalize_gfm_pipe_tables";
import { normalizeMathMarkdown } from "@/lib/normalize_math_markdown";

/**
 * Pre-process assistant markdown for ReactMarkdown (GFM + math).
 * Order: fix tables first, then math delimiters (fences preserved in each step).
 */
export function normalizeChatAssistantMarkdown(source: string): string {
  return normalizeMathMarkdown(normalizeGfmPipeTables(source));
}

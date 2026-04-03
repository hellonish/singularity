import type { LlmCatalogModel } from "@/lib/api";

export type LlmModelGroup = readonly [string, LlmCatalogModel[]];

/**
 * Purpose: Group catalog models by provider in a stable order for pickers (chat bar + ChatPanel).
 */
export function llmModelGroupsFromCatalog(
  models: LlmCatalogModel[] | undefined,
): LlmModelGroup[] {
  const list = models ?? [];
  const g = new Map<string, LlmCatalogModel[]>();
  for (const m of list) {
    const arr = g.get(m.provider) ?? [];
    arr.push(m);
    g.set(m.provider, arr);
  }
  const order = ["grok", "gemini", "deepseek"] as const;
  return order.filter((k) => g.has(k)).map((k) => [k, g.get(k)!] as const);
}

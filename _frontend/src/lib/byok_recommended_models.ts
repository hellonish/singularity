/**
 * Curated “most used” chat models per provider (model_id must exist in backend catalog).
 * Shown on Profile after the user saves a key for that provider.
 */
export type ByokRecommendedRow = {
  model_id: string;
  label: string;
  note: string;
};

export const BYOK_PROVIDER_OPTIONS: { id: string; label: string }[] = [
  { id: "grok", label: "xAI (Grok)" },
  { id: "gemini", label: "Google (Gemini)" },
  { id: "deepseek", label: "DeepSeek" },
];

export const BYOK_RECOMMENDED_MODELS: Record<string, ByokRecommendedRow[]> = {
  grok: [
    {
      model_id: "grok-3-mini",
      label: "Grok 3 Mini",
      note: "Default in chat — fast, efficient for most turns",
    },
    {
      model_id: "grok-3-mini-fast",
      label: "Grok 3 Mini Fast",
      note: "Lower-latency variant",
    },
    {
      model_id: "grok-3",
      label: "Grok 3",
      note: "Flagship quality for harder prompts",
    },
  ],
  gemini: [
    {
      model_id: "gemini-2.5-flash-preview-04-17",
      label: "Gemini 2.5 Flash",
      note: "Fast · general and everyday use",
    },
    {
      model_id: "gemini-2.5-pro-preview-03-25",
      label: "Gemini 2.5 Pro",
      note: "Flagship · complex analysis and long context",
    },
    {
      model_id: "gemini-2.0-flash",
      label: "Gemini 2.0 Flash",
      note: "Stable fast option · multimodal",
    },
    {
      model_id: "gemini-2.0-flash-thinking-exp",
      label: "Gemini 2.0 Flash Thinking",
      note: "Reasoning-style traces · exploratory work",
    },
  ],
  deepseek: [
    {
      model_id: "deepseek-chat",
      label: "DeepSeek V3",
      note: "Standard chat · efficient",
    },
    {
      model_id: "deepseek-reasoner",
      label: "DeepSeek R1 (Reasoner)",
      note: "Chain-of-thought · math and logic",
    },
  ],
};

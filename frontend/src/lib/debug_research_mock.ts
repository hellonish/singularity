/**
 * Debug mock research UI is shown only for this Google account (must match API allowlist).
 */
export const DEBUG_MOCK_RESEARCH_EMAIL = "nish2002.sharma@gmail.com";

export function showDebugMockResearchControls(
  sessionEmail: string | null | undefined,
): boolean {
  return (sessionEmail ?? "").trim().toLowerCase() === DEBUG_MOCK_RESEARCH_EMAIL;
}

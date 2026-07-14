// Client for the database-backed, at-most-once walkthrough endpoints.
//
// The API is the sole source of truth for walkthrough progress. Never cache
// claim, completion, or dismissal state in the browser: the same user must see
// the same result across browsers and devices.

import { authFetch } from '@/lib/auth';

export const WALKTHROUGH_KEY = 'main-dashboard-tour';
export const WALKTHROUGH_VERSION = 1;

async function post(path: string): Promise<Response> {
  return authFetch(`/walkthroughs/${WALKTHROUGH_KEY}/${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ version: WALKTHROUGH_VERSION }),
  });
}

// Attempt to claim the walkthrough. Returns true only for the single caller
// that wins the database claim; already-seen users and concurrent tabs get false.
export async function claimWalkthrough(): Promise<boolean> {
  let response: Response;
  try {
    response = await post('claim');
  } catch {
    // The API is unavailable, so there is no trustworthy claim result.
    return false;
  }
  if (!response.ok) return false;

  const result = (await response.json()) as { show?: boolean };
  return result.show === true;
}

// Idempotent terminal signals. The server persists both terminal states.
export async function completeWalkthrough(): Promise<void> {
  try {
    await post('complete');
  } catch {
    // Best effort; the row remains claimed and will not be granted again.
  }
}

export async function dismissWalkthrough(): Promise<void> {
  try {
    await post('dismiss');
  } catch {
    // Best effort; see completeWalkthrough.
  }
}

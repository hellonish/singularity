/**
 * SSE helper for consuming server-sent events with auth token support.
 */
export async function* consumeSSE(
  url: string,
  token?: string,
): AsyncGenerator<{ event: string; data: string; id?: string }> {
  const headers: Record<string, string> = {
    Accept: "text/event-stream",
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(url, { headers });
  if (!response.ok) {
    throw new Error(`SSE connection failed: ${response.status}`);
  }

  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let currentEvent = "message";
  let currentData = "";
  let currentId: string | undefined;

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (line.startsWith("event: ")) {
          currentEvent = line.slice(7).trim();
        } else if (line.startsWith("data: ")) {
          currentData += line.slice(6);
        } else if (line.startsWith("id: ")) {
          currentId = line.slice(4).trim();
        } else if (line === "") {
          // End of event
          if (currentData) {
            yield { event: currentEvent, data: currentData, id: currentId };
          }
          currentEvent = "message";
          currentData = "";
          currentId = undefined;
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

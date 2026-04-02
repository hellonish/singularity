/**
 * Chat store — manages active chat thread state.
 */
import { create } from "zustand";
import type { MessageResponse } from "@/lib/api";

interface ChatState {
  threadId: string | null;
  messages: MessageResponse[];
  isStreaming: boolean;
  streamingContent: string;

  setThread: (id: string) => void;
  setMessages: (messages: MessageResponse[]) => void;
  addMessage: (message: MessageResponse) => void;
  setStreaming: (streaming: boolean) => void;
  appendStreamToken: (token: string) => void;
  finalizeStream: () => void;
  reset: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  threadId: null,
  messages: [],
  isStreaming: false,
  streamingContent: "",

  setThread: (id) => set({ threadId: id }),

  setMessages: (messages) => set({ messages }),

  addMessage: (message) =>
    set((s) => ({ messages: [...s.messages, message] })),

  setStreaming: (streaming) =>
    set({ isStreaming: streaming, streamingContent: "" }),

  appendStreamToken: (token) =>
    set((s) => ({ streamingContent: s.streamingContent + token })),

  finalizeStream: () =>
    set((s) => {
      const assistantMsg: MessageResponse = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: s.streamingContent,
        token_count: null,
        created_at: new Date().toISOString(),
      };
      return {
        isStreaming: false,
        streamingContent: "",
        messages: [...s.messages, assistantMsg],
      };
    }),

  reset: () =>
    set({
      threadId: null,
      messages: [],
      isStreaming: false,
      streamingContent: "",
    }),
}));

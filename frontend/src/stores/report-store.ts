/**
 * Report store — manages the currently viewed report state.
 */
import { create } from "zustand";
import type { VersionContent } from "@/lib/api";

interface ReportState {
  reportId: string | null;
  content: string;
  versionNum: number;
  etag: string;
  isLoading: boolean;
  chatPanelOpen: boolean;
  selectedText: string | null;
  selectionRange: { start: number; end: number } | null;

  setReport: (id: string, content: VersionContent) => void;
  setLoading: (loading: boolean) => void;
  toggleChatPanel: () => void;
  setChatPanelOpen: (open: boolean) => void;
  setSelection: (text: string | null, range?: { start: number; end: number } | null) => void;
  updateContent: (content: VersionContent) => void;
  reset: () => void;
}

const initialState = {
  reportId: null,
  content: "",
  versionNum: 0,
  etag: "",
  isLoading: false,
  chatPanelOpen: false,
  selectedText: null,
  selectionRange: null,
};

export const useReportStore = create<ReportState>((set) => ({
  ...initialState,

  setReport: (id, version) =>
    set({
      reportId: id,
      content: version.content,
      versionNum: version.version_num,
      etag: version.etag,
      isLoading: false,
    }),

  setLoading: (loading) => set({ isLoading: loading }),

  toggleChatPanel: () =>
    set((s) => ({ chatPanelOpen: !s.chatPanelOpen })),

  setChatPanelOpen: (open) => set({ chatPanelOpen: open }),

  setSelection: (text, range = null) =>
    set({ selectedText: text, selectionRange: range }),

  updateContent: (version) =>
    set({
      content: version.content,
      versionNum: version.version_num,
      etag: version.etag,
    }),

  reset: () => set(initialState),
}));

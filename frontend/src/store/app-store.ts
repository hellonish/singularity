import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { OB_STEPS } from '@/lib/dummy-data';
import { completeWalkthrough } from '@/lib/walkthrough';

export const ACCENT_COLORS = [
  '#7c5230',
  '#0d4c3c',
  '#7ba05b',
  '#6366f1',
  '#785964',
  '#d94a38',
];

export type Theme = 'light' | 'dark' | 'system';
export type ViewMode = 'grid' | 'chat' | 'report' | 'prepare' | 'run';
export type SearchMode = 'research' | 'chat';
export type ResearchApprovalMode = 'ask' | 'auto';
export type Intensity = 'instant' | 'medium' | 'high' | 'ultra';
export type MenuType = 'mode' | 'approval' | 'effort' | 'model' | 'thread' | 'rmodel' | null;

interface AppState {
  theme: Theme;
  accent: string;
  sidebarOpen: boolean;
  mobileSidebarOpen: boolean;
  mobileReportChatOpen: boolean;
  view: ViewMode;
  mode: SearchMode;
  intensity: Intensity;
  modelId: string;
  openMenu: MenuType;
  chatCollapsed: boolean;
  settingsOpen: boolean;
  activeSettingsTab: 'models' | 'appearance';
  userMenuOpen: boolean;
  onboarding: boolean;
  obStep: number;
  provider: string;
  openProvider: string | null;
  // Onboarding drives the provider dropdown: force it open and pre-highlight an
  // option (hover-style) so the tour can point the tip at a specific provider.
  forceProviderMenuOpen: boolean;
  providerHighlight: string | null;
  composerDraft: string;
  activeReportId: string | null;
  activeChatId: string | null;
  activeRunId: string | null;
  activePreparationId: string | null;
  researchApprovalMode: ResearchApprovalMode;

  setTheme: (theme: Theme) => void;
  setAccent: (accent: string) => void;
  toggleSidebar: () => void;
  setMobileSidebarOpen: (open: boolean) => void;
  setMobileReportChatOpen: (open: boolean) => void;
  setView: (view: ViewMode) => void;
  setMode: (mode: SearchMode) => void;
  setIntensity: (intensity: Intensity) => void;
  setModelId: (id: string) => void;
  setOpenMenu: (menu: MenuType) => void;
  toggleChatCollapsed: () => void;
  setSettingsOpen: (open: boolean) => void;
  setActiveSettingsTab: (tab: 'models' | 'appearance') => void;
  setUserMenuOpen: (open: boolean) => void;
  setOnboarding: (onboarding: boolean) => void;
  setObStep: (step: number) => void;
  // Called by real UI actions (clicking Settings, a provider, Save) so the
  // onboarding tour advances only when the user actually performs the step.
  obAdvance: (action: string) => void;
  setProvider: (provider: string) => void;
  setOpenProvider: (provider: string | null) => void;
  setForceProviderMenuOpen: (open: boolean) => void;
  setProviderHighlight: (id: string | null) => void;
  setComposerDraft: (draft: string) => void;
  setActiveReportId: (id: string | null) => void;
  setActiveChatId: (id: string | null) => void;
  setActiveRunId: (id: string | null) => void;
  setActivePreparationId: (id: string | null) => void;
  setResearchApprovalMode: (mode: ResearchApprovalMode) => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
  theme: 'system',
  accent: '#7c5230',
  sidebarOpen: true,
  mobileSidebarOpen: false,
  mobileReportChatOpen: false,
  view: 'grid',
  mode: 'chat',
  intensity: 'medium',
  modelId: 'openai/gpt-oss-20b',
  openMenu: null,
  chatCollapsed: false,
  settingsOpen: false,
  activeSettingsTab: 'models',
  userMenuOpen: false,
  onboarding: false, // Enabled only after the server grants an at-most-once claim

  obStep: 0,
  provider: 'groq',
  openProvider: null,
  forceProviderMenuOpen: false,
  providerHighlight: null,
  composerDraft: '',
  activeReportId: null,
  activeChatId: null,
  activeRunId: null,
  activePreparationId: null,
  researchApprovalMode: 'ask',

  setTheme: (theme) => {
    set({ theme });
    applyThemeAndAccent(theme, useAppStore.getState().accent);
  },
  setAccent: (accent) => {
    set({ accent });
    applyThemeAndAccent(useAppStore.getState().theme, accent);
  },
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setMobileSidebarOpen: (mobileSidebarOpen) => set({ mobileSidebarOpen }),
  setMobileReportChatOpen: (mobileReportChatOpen) => set({ mobileReportChatOpen }),
  setView: (view) => set({ view }),
  setMode: (mode) => set({ mode }),
  setIntensity: (intensity) => set({ intensity }),
  setModelId: (modelId) => set({ modelId }),
  setOpenMenu: (openMenu) => set({ openMenu }),
  toggleChatCollapsed: () => set((state) => ({ chatCollapsed: !state.chatCollapsed })),
  setSettingsOpen: (settingsOpen) => set({ settingsOpen }),
  setActiveSettingsTab: (activeSettingsTab) => set({ activeSettingsTab }),
  setUserMenuOpen: (userMenuOpen) => set({ userMenuOpen }),
  setOnboarding: (onboarding) => set({ onboarding }),
  setObStep: (obStep) => set({ obStep }),
  obAdvance: (action) => set((state) => {
    if (!state.onboarding) return {};
    const step = OB_STEPS[state.obStep];
    if (!step || step.advanceOn !== action) return {};
    const next = state.obStep + 1;
    if (next >= OB_STEPS.length) {
      // Advancing past the last step completes the walkthrough; tell the server
      // (idempotent) so it is never shown again on any device.
      void completeWalkthrough();
      return { onboarding: false };
    }
    return { obStep: next };
  }),
  setProvider: (provider) => set({ provider }),
  setOpenProvider: (openProvider) => set({ openProvider }),
  setForceProviderMenuOpen: (forceProviderMenuOpen) => set({ forceProviderMenuOpen }),
  setProviderHighlight: (providerHighlight) => set({ providerHighlight }),
  setComposerDraft: (composerDraft) => set({ composerDraft }),
  setActiveReportId: (activeReportId) => set({ activeReportId }),
  setActiveChatId: (activeChatId) => set({ activeChatId }),
  setActiveRunId: (activeRunId) => set({ activeRunId }),
  setActivePreparationId: (activePreparationId) => set({ activePreparationId }),
  setResearchApprovalMode: (researchApprovalMode) => set({ researchApprovalMode }),
    }),
    {
      name: 'singularity-storage',
      partialize: (state) => ({
        theme: state.theme,
        accent: state.accent,
        settingsOpen: state.settingsOpen,
        activeSettingsTab: state.activeSettingsTab,
        researchApprovalMode: state.researchApprovalMode,
        activePreparationId: state.activePreparationId,
        activeRunId: state.activeRunId,
      }),
    }
  )
);

// Utility for theme & accent
function hexToRgb(hex: string) {
  const c = hex.replace('#', '');
  return {
    r: parseInt(c.substring(0, 2), 16),
    g: parseInt(c.substring(2, 4), 16),
    b: parseInt(c.substring(4, 6), 16),
  };
}

function hexToRgba(hex: string, alpha: number) {
  const { r, g, b } = hexToRgb(hex);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

export function applyThemeAndAccent(theme: Theme, baseAccent: string) {
  if (typeof document === 'undefined') return;

  const root = document.documentElement;
  if (theme === 'system') {
    const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    root.setAttribute('data-app-theme', isDark ? 'dark' : 'light');
  } else {
    root.setAttribute('data-app-theme', theme);
  }

  root.style.setProperty('--accent', baseAccent);
  root.style.setProperty('--accent-2', baseAccent);
  root.style.setProperty('--accent-soft', hexToRgba(baseAccent, 0.16));
}

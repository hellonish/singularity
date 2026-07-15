'use client';

import { useAppStore } from '@/store/app-store';
import { GridView } from '@/components/views/grid-view';
import { ChatView } from '@/components/views/chat-view';
import { ReportView } from '@/components/views/report-view';
import { ResearchRunView } from '@/components/views/research-run-view';
import { ResearchPreparationView } from '@/components/views/research-preparation-view';

export default function HomePage() {
  const { view } = useAppStore();

  return (
    <>
      {view === 'grid' && <GridView />}
      {view === 'chat' && <ChatView />}
      {view === 'report' && <ReportView />}
      {view === 'prepare' && <ResearchPreparationView />}
      {view === 'run' && <ResearchRunView />}
    </>
  );
}

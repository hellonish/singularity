'use client';

import { useAppStore } from '@/store/app-store';
import { Composer } from '../ui/composer';
import { STANDALONE_CHATS } from '@/lib/dummy-data';

const chatMessages = [
  { who: 'You', text: 'Explain diffusion transformers simply', isUser: true },
  { who: 'Singularity', text: 'Diffusion transformers (DiTs) replace the U-Net backbone commonly used in diffusion models with a Transformer architecture. Instead of spatial convolutions, they treat images as sequences of patches, scaling predictably with more compute.', isUser: false },
];

export function ChatView() {
  const { activeChatId } = useAppStore();
  const chat = STANDALONE_CHATS.find(c => c.id === activeChatId);

  return (
    <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
      <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', overscrollBehavior: 'contain' }}>
        <div style={{ maxWidth: '720px', margin: '0 auto', padding: '90px 24px 24px', display: 'flex', flexDirection: 'column', gap: '22px' }}>
          <h1 style={{ margin: '0 0 20px', fontSize: '24px', fontWeight: 300 }}>{chat?.title}</h1>
          {chatMessages.map((m, i) => (
            <div key={i} style={{ alignSelf: m.isUser ? 'flex-end' : 'flex-start', maxWidth: '85%' }}>
              <div className="sg-mono" style={{ fontSize: '9.5px', letterSpacing: '.1em', textTransform: 'uppercase', color: 'var(--text-faint)', marginBottom: '6px', textAlign: m.isUser ? 'right' : 'left' }}>
                {m.who}
              </div>
              <div style={{ 
                padding: m.isUser ? '12px 16px' : '4px 0', 
                backgroundColor: m.isUser ? 'var(--surface-3)' : 'transparent',
                border: 'none',
                borderRadius: '16px',
                borderTopRightRadius: m.isUser ? '4px' : '16px',
                borderTopLeftRadius: !m.isUser ? '4px' : '16px',
                fontSize: '16px',
                lineHeight: 1.5,
                color: 'var(--text)'
              }}>
                {m.text}
              </div>
            </div>
          ))}
        </div>
      </div>
      <Composer />
    </div>
  );
}

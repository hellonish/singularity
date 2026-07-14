'use client';

import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { useAppStore } from '@/store/app-store';
import { useWorkspace } from '@/components/workspace-provider';
import { Composer } from '../ui/composer';
import { Markdown } from '../ui/markdown';

// How many messages to render initially, and how many more to reveal each time
// the user scrolls near the top of the loaded window.
const INITIAL_WINDOW = 20;
const WINDOW_STEP = 20;

export function ChatView() {
  const { activeChatId } = useAppStore();
  const { chats, messages, loadMessages, streamingChatIds } = useWorkspace();
  const chat = chats.find((item) => item.id === activeChatId);
  const turns = activeChatId ? messages[activeChatId] ?? [] : [];
  const isStreaming = !!activeChatId && streamingChatIds.includes(activeChatId);
  const scrollRef = useRef<HTMLDivElement>(null);
  // Tracks which chat's initial scroll position has already been applied, so
  // the one-time "jump to last user message" doesn't re-fire on every
  // streamed delta (that's the stream-follow effect's job below).
  const positionedChatId = useRef<string | null>(null);

  // Lazy window: instead of mounting every message at once, render only the
  // most recent `visibleCount` turns and reveal older ones as the user scrolls
  // up. Keeps large histories cheap and avoids the abrupt full-list flash.
  const [visibleCount, setVisibleCount] = useState(INITIAL_WINDOW);

  useEffect(() => { if (activeChatId) void loadMessages(activeChatId); }, [activeChatId, loadMessages]);

  useEffect(() => {
    positionedChatId.current = null;
    setVisibleCount(INITIAL_WINDOW);
  }, [activeChatId]);

  // Grow the window if the newly streamed history is longer than what we show,
  // so freshly arrived turns are never hidden below the fold.
  useEffect(() => {
    setVisibleCount((count) => (turns.length > count ? Math.min(turns.length, Math.max(count, INITIAL_WINDOW)) : count));
  }, [turns.length]);

  const hasMore = turns.length > visibleCount;
  const visibleTurns = useMemo(
    () => (hasMore ? turns.slice(turns.length - visibleCount) : turns),
    [turns, visibleCount, hasMore],
  );

  // On first render of a chat's messages, open scrolled to the start of the
  // last user message rather than the top of the whole history. A newly sent
  // message is different: its active SSE response must begin at the bottom so
  // the user immediately sees the pending indicator and incoming tokens.
  useEffect(() => {
    if (!activeChatId || visibleTurns.length === 0) return;
    if (positionedChatId.current === activeChatId) return;
    const el = scrollRef.current;
    if (!el) return;
    positionedChatId.current = activeChatId;
    if (isStreaming) {
      el.scrollTop = el.scrollHeight;
      return;
    }
    const lastUserIndex = [...visibleTurns].reverse().findIndex((message) => message.role === 'user');
    if (lastUserIndex === -1) return;
    const targetId = visibleTurns[visibleTurns.length - 1 - lastUserIndex].id;
    const targetEl = el.querySelector<HTMLElement>(`[data-message-id="${targetId}"]`);
    if (targetEl) targetEl.scrollIntoView({ block: 'start' });
  }, [activeChatId, isStreaming, visibleTurns]);

  // Reveal older messages when the user scrolls near the top. Preserve the
  // visual scroll position across the prepend so the viewport doesn't jump.
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const onScroll = () => {
      if (el.scrollTop > 120) return;
      setVisibleCount((count) => {
        if (count >= turns.length) return count;
        const previousHeight = el.scrollHeight;
        const previousTop = el.scrollTop;
        // Restore position after the taller list paints.
        requestAnimationFrame(() => {
          el.scrollTop = previousTop + (el.scrollHeight - previousHeight);
        });
        return Math.min(turns.length, count + WINDOW_STEP);
      });
    };
    el.addEventListener('scroll', onScroll, { passive: true });
    return () => el.removeEventListener('scroll', onScroll);
  }, [turns.length]);

  // Pin an active reply to the newest token. This intentionally overrides a
  // manual scroll while SSE is in flight: sending a message means the user
  // should see its pending state and every streamed token. Once it completes,
  // the usual near-bottom behavior resumes.
  const lastTurn = turns.at(-1);
  const followKey = `${isStreaming}:${turns.length}:${lastTurn?.content.length ?? 0}`;
  useLayoutEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    if (isStreaming) {
      el.scrollTop = el.scrollHeight;
      return;
    }
    if (positionedChatId.current !== activeChatId) return;
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 160;
    if (nearBottom) el.scrollTop = el.scrollHeight;
  }, [followKey, activeChatId, isStreaming]);

  return <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
    <div ref={scrollRef} style={{ flex: 1, minHeight: 0, overflowY: 'auto', overscrollBehavior: 'contain' }}>
      <div style={{ maxWidth: '720px', margin: '0 auto', padding: '90px 24px 24px', display: 'flex', flexDirection: 'column', gap: '22px' }}>
        <h1 style={{ margin: '0 0 20px', fontSize: '24px', fontWeight: 300 }}>{chat?.title || 'New chat'}</h1>
        {hasMore && <div className="sg-mono" style={{ alignSelf: 'center', fontSize: '9.5px', letterSpacing: '.1em', textTransform: 'uppercase', color: 'var(--text-faint)' }}>Scroll up for earlier messages</div>}
        {visibleTurns.map((message) => <div key={message.id} data-message-id={message.id} style={{ alignSelf: message.role === 'user' ? 'flex-end' : 'flex-start', maxWidth: '85%' }}>
          <div className="sg-mono" style={{ fontSize: '9.5px', letterSpacing: '.1em', textTransform: 'uppercase', color: 'var(--text-faint)', marginBottom: '6px', textAlign: message.role === 'user' ? 'right' : 'left' }}>{message.role === 'user' ? 'You' : 'Singularity'}</div>
          {message.pending ? (
            <div className="sg-thinking" aria-label="Singularity is thinking"><span /><span /><span /></div>
          ) : (
            <div className="chat-message-content" style={{ padding: message.role === 'user' ? '12px 16px' : '4px 0', backgroundColor: message.role === 'user' ? 'var(--surface-3)' : 'transparent', borderRadius: '16px', borderTopRightRadius: message.role === 'user' ? '4px' : '16px', borderTopLeftRadius: message.role === 'user' ? '16px' : '4px', fontSize: '16px', lineHeight: 1.5 }}>{message.content ? <Markdown>{message.content}</Markdown> : '…'}</div>
          )}
        </div>)}
      </div>
    </div>
    <Composer />
  </div>;
}

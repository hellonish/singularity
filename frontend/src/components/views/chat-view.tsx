'use client';

import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { useAppStore } from '@/store/app-store';
import { useWorkspace } from '@/components/workspace-provider';
import { Composer } from '../ui/composer';
import { Markdown } from '../ui/markdown';
import type { ProgressStep } from '@/lib/api';

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
      <div style={{ maxWidth: '900px', margin: '0 auto', padding: 'clamp(64px,14vw,90px) clamp(14px,4vw,24px) 24px', display: 'flex', flexDirection: 'column', gap: '22px' }}>
        <h1 style={{ margin: '0 0 20px', fontSize: 'clamp(19px,5vw,24px)', fontWeight: 400 }}>{chat?.title || 'New chat'}</h1>
        {hasMore && <div className="sg-mono" style={{ alignSelf: 'center', fontSize: '9.5px', letterSpacing: '.1em', textTransform: 'uppercase', color: 'var(--text-faint)' }}>Scroll up for earlier messages</div>}
        {visibleTurns.map((message, index) => {
          // This assistant turn is actively streaming its answer when the chat
          // stream is live, it's the final turn, its first token has landed
          // (no longer pending) and it carries text. Used to keep the work trail
          // alive and to soften the streaming answer's trailing edge.
          const isLastTurn = index === visibleTurns.length - 1;
          const answerStreaming = message.role === 'assistant' && isStreaming && isLastTurn && !message.pending && !!message.content;
          return <div key={message.id} data-message-id={message.id} style={{ alignSelf: message.role === 'user' ? 'flex-end' : 'flex-start', maxWidth: '92%' }}>
          <div className="sg-mono" style={{ fontSize: '9.5px', letterSpacing: '.1em', textTransform: 'uppercase', color: 'var(--text-faint)', marginBottom: '6px', textAlign: message.role === 'user' ? 'right' : 'left' }}>{message.role === 'user' ? 'You' : 'Singularity'}</div>
          {message.role === 'assistant' && message.progress?.length ? (
            <ProgressTrail steps={message.progress} thinking={!!message.pending} streaming={answerStreaming} />
          ) : null}
          {message.pending ? (
            message.progress?.length ? null : (
              <div className="sg-thinking" aria-label="Singularity is thinking"><span /><span /><span /></div>
            )
          ) : (
            <div className={`chat-message-content${answerStreaming ? ' chat-streaming' : ''}`} style={{ padding: message.role === 'user' ? '12px 16px' : '4px 0', backgroundColor: message.role === 'user' ? 'var(--surface-3)' : 'transparent', borderRadius: '16px', borderTopRightRadius: message.role === 'user' ? '4px' : '16px', borderTopLeftRadius: message.role === 'user' ? '16px' : '4px', fontSize: '16px', lineHeight: 1.5 }}>{message.content ? <Markdown>{message.content}</Markdown> : '…'}</div>
          )}
        </div>;
        })}
      </div>
    </div>
    <Composer />
  </div>;
}

/** The animated work trail: a live vertical rail with a "comet" that tracks
 * progress and a shimmering "thinking" header while the turn is still working,
 * collapsing into a "Thought for Ns · N steps" toggle once the answer streams.
 * A faithful port of the Thinking Process design, driven by the real streamed
 * ProgressStep[]. */
function ProgressTrail({ steps, thinking, streaming = false }: { steps: ProgressStep[]; thinking: boolean; streaming?: boolean }) {
  // While thinking, the trail is always expanded (no toggle); once the answer
  // begins, it collapses behind the "Thought for Ns" summary but can be reopened.
  const [expanded, setExpanded] = useState(false);
  // The trail stays visually "alive" (accent rail, glowing comet) both while
  // thinking and while the answer is still streaming, so it doesn't read as a
  // dead, stale artifact sitting above live text; it settles once fully done.
  const alive = thinking || streaming;
  const showSteps = thinking || expanded;
  const showToggle = !thinking;

  // Wall-clock think time: captured when thinking begins and frozen the moment
  // it ends, so "Thought for Ns" stays stable after the answer streams.
  const startRef = useRef<number>(Date.now());
  const [thoughtSecs, setThoughtSecs] = useState(0);
  const wasThinking = useRef(thinking);
  useEffect(() => {
    if (wasThinking.current && !thinking) {
      setThoughtSecs(Math.max(1, Math.round((Date.now() - startRef.current) / 1000)));
    }
    wasThinking.current = thinking;
  }, [thinking]);

  const total = steps.length;
  const doneCount = steps.filter((step) => step.done || step.failed).length;
  const frac = total ? doneCount / total : 0;
  const pct = Math.round(frac * 100);
  const latest = steps[total - 1];
  // The single step the model is actively on: the last one that hasn't resolved.
  const runningIndex = thinking ? steps.findIndex((step) => !step.done && !step.failed) : -1;

  return (
    <div style={{ position: 'relative', padding: '2px 0 2px 18px', marginBottom: '10px' }}>
      {/* base rail + progress fill */}
      <span aria-hidden style={{ position: 'absolute', left: 0, top: 3, bottom: 3, width: 2, background: 'var(--border)', borderRadius: 2 }} />
      <span aria-hidden style={{ position: 'absolute', left: 0, top: 3, width: 2, height: `${pct}%`, maxHeight: 'calc(100% - 6px)', background: alive ? 'var(--accent-2)' : 'var(--border-strong)', borderRadius: 2, transition: 'height .55s cubic-bezier(.4,0,.2,1)' }} />
      {/* comet head + tail — visible while the turn is still working */}
      {alive ? (
        <>
          <span aria-hidden style={{ position: 'absolute', left: 0, top: `calc(${pct}% - 26px)`, width: 2, height: 26, borderRadius: 2, background: 'linear-gradient(to bottom,transparent,var(--accent-2))', opacity: 0.55, transition: 'top .55s cubic-bezier(.4,0,.2,1)' }} />
          <span aria-hidden style={{ position: 'absolute', left: -3, top: `calc(${pct}% - 1px)`, width: 8, height: 8, borderRadius: '50%', background: 'var(--accent-2)', animation: 'tp-comet 1.4s ease-in-out infinite', transition: 'top .55s cubic-bezier(.4,0,.2,1)' }} />
        </>
      ) : null}

      {/* thinking header */}
      {thinking ? (
        <div aria-live="polite" style={{ display: 'flex', alignItems: 'center', gap: 11, marginBottom: 13 }}>
          <span aria-hidden style={{ position: 'relative', width: 15, height: 15, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--accent-2)', animation: 'tp-breathe 1.2s ease-in-out infinite' }} />
            <span style={{ position: 'absolute', inset: 0, border: '1.5px solid transparent', borderTopColor: 'var(--accent-2)', borderRightColor: 'var(--accent-2)', borderRadius: '50%', animation: 'tp-spin 1s linear infinite', opacity: 0.7 }} />
          </span>
          <span className="tp-shimmer" style={{ fontSize: 15, fontStyle: 'italic' }}>Singularity is thinking</span>
          {latest ? (
            <span className="sg-mono" style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--text-faint)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '46%' }}>{latest.label}</span>
          ) : null}
        </div>
      ) : null}

      {/* collapse toggle */}
      {showToggle ? (
        <button
          type="button"
          onClick={() => setExpanded((value) => !value)}
          className="sg-mono"
          aria-expanded={expanded}
          style={{ display: 'inline-flex', alignItems: 'center', gap: 8, alignSelf: 'flex-start', padding: '5px 11px 5px 9px', border: '1px solid var(--border)', background: 'var(--surface-2)', borderRadius: 8, cursor: 'pointer', fontSize: 11.5, color: 'var(--text-dim)' }}
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.4} style={{ transition: 'transform .25s ease', transform: `rotate(${expanded ? 0 : -90}deg)` }}><polyline points="6 9 12 15 18 9" /></svg>
          {expanded ? 'Hide work' : `Thought for ${thoughtSecs}s · ${total} step${total === 1 ? '' : 's'}`}
        </button>
      ) : null}

      {/* step list */}
      {showSteps ? (
        <div style={{ display: 'flex', flexDirection: 'column', marginTop: thinking ? 2 : 10, animation: 'tp-collapse .3s ease both', overflow: 'hidden' }}>
          {steps.map((step, index) => {
            const running = index === runningIndex;
            // Only finished steps carry a real duration; a running step has no
            // per-step start timestamp in the stream, so we don't fake a timer.
            const elapsed = !running && typeof step.elapsedSeconds === 'number' ? `${step.elapsedSeconds.toFixed(1)}s` : '';
            return (
              <div key={index} style={{ display: 'flex', gap: 9, alignItems: 'flex-start', padding: '3px 0', animation: 'tp-inx .28s ease both' }}>
                <span aria-hidden style={{ flexShrink: 0, width: 15, display: 'flex', alignItems: 'center', justifyContent: 'center', marginTop: 3 }}>
                  {running ? (
                    <span style={{ position: 'relative', width: 13, height: 13, display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
                      <span style={{ width: 5, height: 5, borderRadius: '50%', background: 'var(--accent-2)', animation: 'tp-breathe 1.1s ease-in-out infinite' }} />
                      <span style={{ position: 'absolute', inset: 0, border: '1.4px solid transparent', borderTopColor: 'var(--accent-2)', borderRadius: '50%', animation: 'tp-spin .8s linear infinite' }} />
                    </span>
                  ) : step.failed ? (
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="var(--warn)" strokeWidth={2.1}><path d="M12 9v4M12 17h.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" /></svg>
                  ) : step.done ? (
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="var(--ok)" strokeWidth={2.6} style={{ animation: 'tp-pop .32s cubic-bezier(.2,.8,.2,1) both' }}><polyline points="20 6 9 17 4 12" /></svg>
                  ) : (
                    <span style={{ width: 5, height: 5, borderRadius: '50%', background: 'var(--text-faint)' }} />
                  )}
                </span>
                <span
                  className={running ? 'tp-shimmer' : undefined}
                  style={{ flex: 1, minWidth: 0, fontSize: 14.5, fontStyle: 'italic', lineHeight: 1.45, color: running ? undefined : step.failed ? 'var(--warn)' : 'var(--text-dim)' }}
                >{step.label}</span>
                {elapsed ? (
                  <span className="sg-mono" style={{ flexShrink: 0, marginLeft: 'auto', paddingLeft: 10, fontSize: 11, color: 'var(--text-faint)' }}>{elapsed}</span>
                ) : null}
              </div>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}

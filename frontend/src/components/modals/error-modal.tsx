'use client';

import { useEffect, useRef } from 'react';
import { useWorkspace } from '@/components/workspace-provider';

interface ErrorDialogProps {
  error: string | null;
  onDismiss: () => void;
}

/** A readable, focusable surface for a user-facing failure. */
export function ErrorDialog({ error, onDismiss }: ErrorDialogProps) {
  const dismissButton = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!error) return;
    dismissButton.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onDismiss();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [error, onDismiss]);

  if (!error) return null;

  return (
    <div
      role="alertdialog"
      aria-modal="true"
      aria-labelledby="workspace-error-title"
      aria-describedby="workspace-error-message"
      onClick={onDismiss}
      style={{ position: 'fixed', inset: 0, zIndex: 100, backgroundColor: 'rgba(6,9,14,0.68)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '24px' }}
    >
      <section
        onClick={(event) => event.stopPropagation()}
        style={{ width: 'min(560px, 100%)', maxHeight: 'min(72vh, 620px)', display: 'flex', flexDirection: 'column', backgroundColor: 'var(--surface)', borderRadius: '18px', boxShadow: 'var(--shadow)', overflow: 'hidden' }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '11px', padding: '18px 20px', borderBottom: '1px solid var(--border)' }}>
          <span aria-hidden="true" style={{ display: 'grid', placeItems: 'center', width: '25px', height: '25px', borderRadius: '50%', backgroundColor: 'color-mix(in srgb, var(--color-danger) 18%, transparent)', color: 'var(--color-danger)', fontWeight: 500 }}>!</span>
          <div id="workspace-error-title" style={{ fontSize: '18px', fontWeight: 500, color: 'var(--text)' }}>Something went wrong</div>
        </div>
        <div id="workspace-error-message" style={{ padding: '20px', overflowY: 'auto', color: 'var(--text)', fontSize: '14.5px', lineHeight: 1.6, whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>
          {error}
        </div>
        <div style={{ display: 'flex', justifyContent: 'flex-end', padding: '14px 20px', borderTop: '1px solid var(--border)' }}>
          <button
            ref={dismissButton}
            type="button"
            onClick={onDismiss}
            style={{ height: '36px', padding: '0 16px', border: 'none', borderRadius: '9px', backgroundColor: 'var(--accent)', color: '#fff', cursor: 'pointer', fontSize: '13px', fontWeight: 500 }}
          >
            Dismiss
          </button>
        </div>
      </section>
    </div>
  );
}

/** Displays workspace failures above every dashboard view, rather than in a composer hint. */
export function ErrorModal() {
  const { error, clearError } = useWorkspace();
  return <ErrorDialog error={error} onDismiss={clearError} />;
}

'use client';

import { useEffect, useRef, useState } from 'react';
import { useAppStore } from '@/store/app-store';
import { OB_STEPS, OB_STARTER_MESSAGE, PROVIDERS } from '@/lib/dummy-data';

const SCRIM = 'rgba(6,9,14,0.74)';

export function Spotlight() {
  const {
    onboarding, obStep, setObStep, setOnboarding,
    setSettingsOpen, setUserMenuOpen, setView, setMode,
    openProvider, setOpenProvider, setComposerDraft,
  } = useAppStore();
  const [tourRect, setTourRect] = useState<{ x: number, y: number, w: number, h: number } | null>(null);
  const typedRef = useRef(false);

  const step = OB_STEPS[obStep];
  const isLast = obStep === OB_STEPS.length - 1;

  // Keep the underlying UI in the right state for whichever step we're on. This
  // runs on every step change so the highlight target actually exists on screen.
  useEffect(() => {
    if (!onboarding || !step) return;
    switch (step.target) {
      case 'menu-settings':
        setUserMenuOpen(true); setSettingsOpen(false);
        break;
      case 'providers':
        setUserMenuOpen(false); setSettingsOpen(true); setOpenProvider(null);
        break;
      case 'keysetup':
        // Keep whatever provider the user picked in the previous step; only fall
        // back to the first one if somehow none is selected.
        setUserMenuOpen(false); setSettingsOpen(true);
        if (!openProvider) setOpenProvider(PROVIDERS[0].id);
        break;
      case 'composer':
        setSettingsOpen(false); setUserMenuOpen(false); setView('grid'); setMode('chat');
        break;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [onboarding, obStep]);

  // Measure the highlight target. Instead of guessing with a fixed timeout, we
  // poll on each animation frame until the target exists AND its layout has
  // settled (two identical measurements in a row) — the target may still be
  // animating/scrolling into place inside the modal. We only publish tourRect
  // once we have a real, stable rect, so the cutout never flashes in the wrong
  // spot; it simply appears (and CSS-glides) at the correct position.
  useEffect(() => {
    if (!onboarding || !step) {
      setTourRect(null);
      return;
    }
    const scrollTargets = ['keysetup'];
    const selector = `[data-tour="${step.target}"]`;

    // A new step's target isn't the previous one — clear so we never show a
    // cutout at a stale position while the new target lays out.
    setTourRect(null);

    let raf = 0;
    let prev: string | null = null;    // last measured rect, serialized
    let stableFrames = 0;
    let scrolled = false;
    let frames = 0;
    const MAX_FRAMES = 180;            // ~3s safety cap, then give up gracefully

    const tick = () => {
      frames += 1;
      const el = document.querySelector(selector);
      if (el) {
        if (!scrolled && scrollTargets.includes(step.target)) {
          el.scrollIntoView({ block: 'center', behavior: 'auto' });
          scrolled = true;
        }
        const r = el.getBoundingClientRect();
        if (r.width > 0 && r.height > 0) {
          const key = `${Math.round(r.left)},${Math.round(r.top)},${Math.round(r.width)},${Math.round(r.height)}`;
          stableFrames = key === prev ? stableFrames + 1 : 0;
          prev = key;
          // Two consecutive identical frames ⇒ layout has settled.
          if (stableFrames >= 2) {
            setTourRect({ x: Math.round(r.left), y: Math.round(r.top), w: Math.round(r.width), h: Math.round(r.height) });
            return;
          }
        }
      }
      if (frames < MAX_FRAMES) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);

    // Keep the highlight glued to the target on window resize (re-run the poll).
    const onResize = () => { frames = 0; prev = null; stableFrames = 0; raf = requestAnimationFrame(tick); };
    window.addEventListener('resize', onResize);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('resize', onResize);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [onboarding, obStep]);

  // Final step: "type" the starter message into the composer, character by
  // character, then dismiss the dimming overlay leaving the text in the box.
  useEffect(() => {
    if (!onboarding || !isLast || typedRef.current) return;
    typedRef.current = true;

    let i = 0;
    const type = () => {
      i += 1;
      setComposerDraft(OB_STARTER_MESSAGE.slice(0, i));
      if (i < OB_STARTER_MESSAGE.length) {
        timer = window.setTimeout(type, 26);
      } else {
        // Message is fully typed — clear the overlay so the user can press Enter.
        end = window.setTimeout(() => setOnboarding(false), 850);
      }
    };
    let timer = window.setTimeout(type, 350);
    let end = 0;

    return () => { clearTimeout(timer); clearTimeout(end); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [onboarding, isLast]);

  if (!onboarding || !step) return null;

  // Geometry for the cutout + tooltip.
  let tooltipStyle: any = null;
  let hole: { x: number, y: number, w: number, h: number, r: number } | null = null;

  const vw = typeof window !== 'undefined' ? window.innerWidth : 1280;
  const vh = typeof window !== 'undefined' ? window.innerHeight : 800;

  if (tourRect) {
    const pad = 8;
    const sx = tourRect.x - pad;
    const sy = tourRect.y - pad;
    const sw = tourRect.w + pad * 2;
    const sh = tourRect.h + pad * 2;
    // A modest, consistent rounding — not a fully-rounded pill.
    const radius = Math.min(14, sw / 2, sh / 2);
    hole = { x: sx, y: sy, w: sw, h: sh, r: radius };

    const cardW = 264;
    const cardH = 260;
    const ty = tourRect.y + tourRect.h / 2;
    const targetTop = ty < vh * 0.5;

    tooltipStyle = {
      position: 'fixed',
      width: `${cardW}px`,
      backgroundColor: 'var(--surface)',
      border: '1px solid var(--border-strong)',
      borderRadius: '12px',
      boxShadow: 'var(--shadow)',
      padding: '14px 16px',
      zIndex: 68,
    };

    const isWideTarget = sw > vw * 0.4;
    const roomOnRight = vw - (sx + sw) > cardW + 24;

    if (isWideTarget) {
      tooltipStyle.top = Math.max(12, Math.min(sy, vh - cardH - 12));
      tooltipStyle.left = roomOnRight ? sx + sw + 16 : Math.max(12, sx - cardW - 16);
    } else {
      tooltipStyle.left = Math.max(12, Math.min(sx, vw - cardW - 12));
      if (targetTop) tooltipStyle.top = sy + sh + 16;
      else tooltipStyle.bottom = vh - sy + 16;
    }
  }

  // Invisible hit-blockers around the hole keep everything except the target
  // un-clickable, without drawing anything (the box-shadow provides the dim).
  const blocker = (s: React.CSSProperties): React.CSSProperties => ({
    position: 'fixed', zIndex: 64, ...s,
  });

  return (
    <div data-screen-label="Onboarding">
      {/* Full-screen dim, shown until we have a real measurement so the cutout
          never appears at a wrong position. It fades out as the hole takes over. */}
      <div style={{ position: 'fixed', inset: 0, backgroundColor: SCRIM, zIndex: 63, opacity: hole ? 0 : 1, transition: 'opacity .2s ease', pointerEvents: hole ? 'none' : 'auto' }} />

      {hole && (
        <>
          {/* Click-blockers (invisible) around the interactive target */}
          <div style={blocker({ left: 0, top: 0, width: '100vw', height: Math.max(0, hole.y) })} />
          <div style={blocker({ left: 0, top: hole.y + hole.h, width: '100vw', height: Math.max(0, vh - (hole.y + hole.h)) })} />
          <div style={blocker({ left: 0, top: hole.y, width: Math.max(0, hole.x), height: hole.h })} />
          <div style={blocker({ left: hole.x + hole.w, top: hole.y, width: Math.max(0, vw - (hole.x + hole.w)), height: hole.h })} />
          {/* The highlight: a hole-sized box whose giant box-shadow IS the dim, with
              the accent border. Clicks pass through; position/size CSS-glide. */}
          <div
            style={{
              position: 'fixed',
              left: hole.x, top: hole.y, width: hole.w, height: hole.h,
              borderRadius: hole.r,
              border: '2px solid var(--accent-2)',
              boxShadow: `0 0 0 9999px ${SCRIM}`,
              zIndex: 65,
              pointerEvents: 'none',
              transition: 'left .28s cubic-bezier(.2,.8,.2,1), top .28s cubic-bezier(.2,.8,.2,1), width .28s cubic-bezier(.2,.8,.2,1), height .28s cubic-bezier(.2,.8,.2,1)',
            }}
          />
        </>
      )}

      {obStep === 0 && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 67, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', pointerEvents: 'none' }} className="animate-sg-pop">
          <h1 style={{ color: '#fff', fontSize: '32px', fontWeight: 300, fontStyle: 'italic', marginBottom: '16px', textAlign: 'center', textShadow: '0 2px 10px rgba(0,0,0,0.5)' }}>
            Welcome to Singularity, Nishant
          </h1>
          <p style={{ color: 'rgba(255,255,255,0.7)', fontSize: '18px', textAlign: 'center', textShadow: '0 2px 10px rgba(0,0,0,0.5)' }}>
            Just a few steps to setup your account.
          </p>
        </div>
      )}

      {tooltipStyle && (
        <div style={tooltipStyle} className="animate-sg-pop">
          <h3 style={{ margin: '0 0 6px', fontSize: '15px', fontWeight: 500, color: 'var(--text)' }}>{step.title}</h3>
          <p style={{ margin: '0 0 12px', fontSize: '13.5px', lineHeight: 1.5, color: 'var(--text-dim)' }}>{step.desc}</p>

          {/* Persistent "do this right now" instruction box */}
          <div style={{ display: 'flex', gap: '9px', alignItems: 'flex-start', margin: '0 0 14px', padding: '10px 11px', borderRadius: '10px', backgroundColor: 'var(--accent-soft)', border: '1px solid var(--accent)' }}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--accent-2)" strokeWidth="2" style={{ flexShrink: 0, marginTop: '1px' }}><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" /></svg>
            <span style={{ fontSize: '12.5px', lineHeight: 1.45, color: 'var(--text)' }}>{step.hint}</span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <button onClick={() => setOnboarding(false)} style={{ background: 'transparent', border: 'none', color: 'var(--text-faint)', fontSize: '11.5px', cursor: 'pointer', padding: 0 }}>Skip tour</button>
            {obStep > 0 && (
              <button onClick={() => setObStep(obStep - 1)} style={{ background: 'transparent', border: 'none', color: 'var(--text-dim)', fontSize: '11.5px', cursor: 'pointer', padding: 0 }}>Back</button>
            )}
            {isLast && (
              <button
                onClick={() => setOnboarding(false)}
                style={{ marginLeft: 'auto', height: '30px', padding: '0 13px', border: 'none', borderRadius: '8px', backgroundColor: 'var(--accent)', color: '#fff', fontFamily: 'var(--font-mono)', fontSize: '11.5px', fontWeight: 500, cursor: 'pointer' }}
              >
                Got it
              </button>
            )}
          </div>
          <div className="sg-mono" style={{ marginTop: '10px', fontSize: '10px', letterSpacing: '.05em', color: 'var(--accent-2)', textAlign: 'right' }}>Step {obStep + 1} / {OB_STEPS.length}</div>
        </div>
      )}
    </div>
  );
}

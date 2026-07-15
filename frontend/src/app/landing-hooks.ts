import { useEffect, useState, useRef, RefObject } from 'react';

// --- Wave Canvas Animation ---
export function useWaveAnimation(waveRef: RefObject<HTMLCanvasElement | null>, accentHex: string) {
  useEffect(() => {
    const canvas = waveRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const host = canvas.parentElement;
    if (!host) return;

    let raf = 0;
    let w = 0, h = 0;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    let mx = -9999, my = -9999;
    let t = 0;
    let ripples: {x: number, y: number, t: number}[] = [];
    let parts: any[] = [];
    let frame = 0;

    const accentRGB = () => {
      let hex = accentHex.replace('#', '');
      if (hex.length !== 6) return [124, 82, 48];
      return [parseInt(hex.slice(0, 2), 16), parseInt(hex.slice(2, 4), 16), parseInt(hex.slice(4, 6), 16)];
    };
    let col = accentRGB();

    const build = () => {
      const n = Math.max(900, Math.round(w * 1.6));
      parts = [];
      for (let i = 0; i < n; i++) {
        parts.push({
          na: Math.random(),
          db: (Math.random() * 2 - 1) * 2.6,
          gph: Math.random() * 40,
          size: 0.9 + Math.random() * 2.2,
          ph: Math.random() * 6.2832,
          sp: 0.4 + Math.random() * 1.1
        });
      }
    };

    const resize = () => {
      const r = canvas.getBoundingClientRect();
      w = r.width;
      h = r.height;
      canvas.width = Math.round(r.width * dpr);
      canvas.height = Math.round(r.height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      build();
    };

    resize();

    const onResize = () => resize();
    const onMove = (e: MouseEvent) => {
      const r = canvas.getBoundingClientRect();
      mx = e.clientX - r.left;
      my = e.clientY - r.top;
    };
    const onLeave = () => { mx = -9999; my = -9999; };
    const onClick = (e: MouseEvent) => {
      const r = canvas.getBoundingClientRect();
      ripples.push({ x: e.clientX - r.left, y: e.clientY - r.top, t: 0 });
      if (ripples.length > 5) ripples.shift();
    };

    window.addEventListener('resize', onResize);
    window.addEventListener('mousemove', onMove);
    host.addEventListener('mouseleave', onLeave);
    host.addEventListener('click', onClick);

    const draw = () => {
      raf = requestAnimationFrame(draw);
      t += 0.011;
      if (frame++ % 20 === 0) col = accentRGB();
      ctx.clearRect(0, 0, w, h);
      const [cr, cg, cb] = col;
      const isoA = Math.PI / 6;
      const ax = Math.cos(isoA), ay = Math.sin(isoA);
      const baseL = h * 0.88, baseR = h * 0.58;
      const tw = h * 0.072;
      const amp = h * 0.10;

      ripples.forEach(rp => rp.t += 0.014);
      ripples = ripples.filter(rp => rp.t < 1.2);

      for (const p of parts) {
        const gx = p.na * 45;
        const bx = p.na * w + p.db * tw * ax;
        const baseY = baseL + (baseR - baseL) * p.na;
        const gyScreen = baseY + p.db * tw * ay;
        let z = Math.sin(gx * 0.52 - t) * amp + Math.cos(gx * 0.29 - p.gph * 0.4 + t * 0.7) * amp * 0.45;
        const dx = bx - mx, dy = gyScreen - my;
        const md = Math.sqrt(dx * dx + dy * dy);
        z -= Math.exp(-(md * md) / (2 * 70 * 70)) * amp * 0.5;
        
        for (const rp of ripples) {
          const rd = Math.hypot(bx - rp.x, gyScreen - rp.y);
          const ring = rp.t * 220;
          z -= Math.exp(-((rd - ring) ** 2) / (2 * 30 * 30)) * amp * 0.5 * (1 - rp.t / 1.2);
        }
        
        const sy = gyScreen - z;
        const nz = Math.max(0, Math.min(1, (z + amp * 1.6) / (amp * 3.4)));
        const near = Math.exp(-(md * md) / (2 * 90 * 90));
        const twk = 0.8 + 0.2 * Math.sin(t * p.sp + p.ph);
        const a = Math.min(0.6, (0.06 + nz * 0.32) * twk + near * 0.12);
        const rad = p.size + nz * 1.4 + near * 0.6;
        
        ctx.fillStyle = `rgba(${cr},${cg},${cb},${a})`;
        ctx.beginPath();
        ctx.arc(bx, sy, rad, 0, 6.2832);
        ctx.fill();
      }
    };
    
    draw();

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('resize', onResize);
      window.removeEventListener('mousemove', onMove);
      host.removeEventListener('mouseleave', onLeave);
      host.removeEventListener('click', onClick);
    };
  }, [waveRef, accentHex]);
}

// --- Reveal Intersection Observer ---
export function useReveal(rootRef: RefObject<HTMLElement | null>) {
  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;
    
    const io = new IntersectionObserver((entries) => {
      entries.forEach(en => {
        if (en.isIntersecting) {
          en.target.classList.add('in');
          io.unobserve(en.target);
        }
      });
    }, { threshold: 0.18, rootMargin: '0px 0px -8% 0px' });

    const els = root.querySelectorAll('.reveal:not(.in)');
    els.forEach(el => io.observe(el));

    return () => io.disconnect();
  }, [rootRef]);
}

// --- Research Scroll ---
export function useResearchScroll(researchRef: RefObject<HTMLElement | null>) {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    let pending = false;
    const onScroll = () => {
      if (pending) return;
      pending = true;
      requestAnimationFrame(() => {
        pending = false;
        const el = researchRef.current;
        if (!el) return;
        const rect = el.getBoundingClientRect();
        const total = el.offsetHeight - window.innerHeight;
        let p = total > 0 ? -rect.top / total : 0;
        p = Math.max(0, Math.min(1, p));
        setProgress(p);
      });
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
    return () => window.removeEventListener('scroll', onScroll);
  }, [researchRef]);

  return progress;
}

// --- Chat Demo Streaming ---
type DemoMessage = { role: 'user' | 'assistant', text: string, streaming?: boolean };
const DEMO_SCRIPT = [
  { role: 'user', text: 'Explain diffusion transformers simply.' },
  { role: 'assistant', text: 'Think of it as an artist who starts with static and removes noise step by step — but instead of a fixed painter, a transformer weighs every patch of the image at once to decide what to keep.' },
  { role: 'user', text: 'Turn that into a full report →' },
  { role: 'assistant', text: 'On it — promoting this thread to Research. Retrieving sources and drafting a cited document now.' },
];

export function useChatDemo() {
  const [demo, setDemo] = useState<{ items: DemoMessage[], typing: boolean }>({ items: [], typing: false });
  const timers = useRef<NodeJS.Timeout[]>([]);

  useEffect(() => {
    const _timer = (fn: () => void, ms: number) => {
      const id = setTimeout(fn, ms);
      timers.current.push(id);
    };

    const streamWords = (words: string[], wi: number, turnIdx: number) => {
      if (wi >= words.length) {
        setDemo(s => {
          const items = [...s.items];
          const last = items[items.length - 1];
          if (last) items[items.length - 1] = { ...last, streaming: false };
          return { ...s, items };
        });
        _timer(() => runTurn(turnIdx + 1), 900);
        return;
      }
      setDemo(s => {
        const items = [...s.items];
        const last = items[items.length - 1];
        items[items.length - 1] = { ...last, text: (last.text ? last.text + ' ' : '') + words[wi] };
        return { ...s, items };
      });
      _timer(() => streamWords(words, wi + 1, turnIdx), 42 + Math.random() * 46);
    };

    const runTurn = (i: number) => {
      if (i >= DEMO_SCRIPT.length) {
        _timer(() => {
          setDemo({ items: [], typing: false });
          _timer(() => runTurn(0), 900);
        }, 3600);
        return;
      }
      const turn = DEMO_SCRIPT[i];
      if (turn.role === 'user') {
        setDemo(s => ({ typing: false, items: [...s.items, { role: 'user', text: turn.text }] }));
        _timer(() => runTurn(i + 1), 750);
      } else {
        setDemo(s => ({ ...s, typing: true }));
        _timer(() => {
          setDemo(s => ({ typing: false, items: [...s.items, { role: 'assistant', text: '', streaming: true }] }));
          streamWords(turn.text.split(' '), 0, i);
        }, 1000);
      }
    };

    _timer(() => runTurn(0), 900);

    return () => {
      timers.current.forEach(clearTimeout);
      timers.current = [];
    };
  }, []);

  return demo;
}

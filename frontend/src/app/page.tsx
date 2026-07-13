"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import { useAppStore, ACCENT_COLORS } from "@/store/app-store";
import { AppLogoMark } from "@/components/app-logo";
import { useWaveAnimation, useResearchScroll, useChatDemo, useReveal } from "./landing-hooks";

import { AgentFlowchart } from "@/components/layout/agent-flowchart";

const PROVIDERS = [
  { name: 'Anthropic', dot: '#d97757', logo: '/reference/logo-anthropic.svg' },
  { name: 'OpenAI', dot: '#10a37f', logo: '/reference/logo-openai.svg' },
  { name: 'DeepSeek', dot: '#4d6bfe', logo: '/reference/logo-deepseek.svg' },
  { name: 'Grok · xAI', dot: '#c9ccd1', logo: '/reference/logo-grok.svg' },
  { name: 'Groq', dot: '#f55036', logo: '/reference/logo-groq.svg' },
  { name: 'OpenRouter', dot: '#ffffff', logo: '/reference/openrouter.svg' },
];

const FOOTER_COLS = [
  { title: 'Product', links: [ { label: 'Research', href: '#research' }, { label: 'Chat', href: '#chat' }, { label: 'Models', href: '#models' } ] },
  { title: 'More', links: [ { label: 'ineedajob.pro', href: 'https://www.ineedajob.pro' }, { label: 'hellonish.dev', href: 'https://www.hellonish.dev' } ] },
];

const TERMINAL_COMMANDS = [
  { cmd: "/help", desc: "About Singularity, usage, privacy, and command reference" },
  { cmd: "/provider", desc: "Choose Groq, DeepSeek, or OpenRouter with arrow keys" },
  { cmd: "/models", desc: "Choose a model for the selected provider" },
  { cmd: "/effort", desc: "Choose chat effort or bounded research depth" },
  { cmd: "/mode", desc: "Choose chat or bounded research mode with arrow keys" },
  { cmd: "/key", desc: "Set, inspect, or remove the selected provider API key" },
  { cmd: "/status", desc: "Show the current model, effort, credentials, tools, and session state" },
  { cmd: "/reset", desc: "Clear this ephemeral conversation history" },
  { cmd: "/clear", desc: "Clear the terminal screen" },
  { cmd: "/quit", desc: "Exit Singularity" },
];

export default function LandingPage() {
  const router = useRouter();
  const { theme, setTheme, accent, setAccent } = useAppStore();
  const themeRef = useRef<HTMLDivElement>(null);
  const waveRef = useRef<HTMLCanvasElement>(null);
  const researchRef = useRef<HTMLElement>(null);
  
  const [accentMenuOpen, setAccentMenuOpen] = useState(false);
  
  // Custom hooks for complex prototype logic
  useWaveAnimation(waveRef, accent);
  useReveal(themeRef);
  const rp = useResearchScroll(researchRef);
  const demo = useChatDemo();

  const isDark = theme === "dark";
  const toggleTheme = () => setTheme(isDark ? "light" : "dark");
  const goDashboard = () => router.push("/login");

  const n = 8;
  const activeIdx = Math.min(n - 1, Math.max(0, Math.floor(rp * n)));
  const isLive = rp >= 0.94;

  return (
    <div ref={themeRef} data-app-theme={theme} style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)', fontFamily: "'Newsreader', Georgia, serif", transition: 'background .3s, color .3s', '--accent': accent, '--accent-2': accent, '--accent-soft': `${accent}22` } as React.CSSProperties}>
      <style dangerouslySetInnerHTML={{ __html: `
        html{scroll-behavior:smooth}
        body{margin:0;background:var(--bg);color:var(--text);-webkit-font-smoothing:antialiased;font-family:'Newsreader',Georgia,serif}
        a{color:var(--accent-2);text-decoration:none} a:hover{color:var(--accent)}
        ::selection{background:var(--accent-soft);color:var(--text)}
        @keyframes lp-rise{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}
        @keyframes lp-grow{from{transform:scaleY(0)}to{transform:scaleY(1)}}
        @keyframes lp-dot{0%,60%,100%{transform:translateY(0);opacity:.35}30%{transform:translateY(-4px);opacity:.9}}
        @keyframes lp-pop{from{opacity:0;transform:translateY(8px) scale(.98)}to{opacity:1;transform:none}}
        @keyframes lp-flow{0%{top:0;opacity:0}8%{opacity:1}92%{opacity:1}100%{top:100%;opacity:0}}
        .lp-mono{font-family:'JetBrains Mono',monospace}
        .reveal{opacity:0;transform:translateY(28px);transition:opacity .7s ease,transform .8s cubic-bezier(.2,.8,.2,1)}
        .reveal.in{opacity:1;transform:none}
        .lp-bar{transform:scaleY(0);transform-origin:bottom;transition:transform .75s cubic-bezier(.2,.8,.2,1) .15s}
        .reveal.in .lp-bar{transform:scaleY(1)}
      ` }} />

      {/* ===== NAV ===== */}
      <header data-screen-label="Nav" style={{ position: 'sticky', top: 0, zIndex: 40, display: 'flex', alignItems: 'center', gap: 20, height: 66, padding: '0 clamp(18px,4vw,44px)', background: 'color-mix(in srgb, var(--bg) 86%, transparent)', backdropFilter: 'blur(10px)', borderBottom: '1px solid var(--border)' }}>
        <a href="#top" style={{ display: 'flex', alignItems: 'center', gap: 10, color: 'var(--text)' }}>
          <AppLogoMark width={28} height={28} />
          <span style={{ fontSize: 19, fontWeight: 500, letterSpacing: '-.01em' }}>Singularity</span>
        </a>
        <nav className="lp-mono hidden sm:flex" style={{ marginLeft: 14, alignItems: 'center', gap: 4, fontSize: 12, letterSpacing: '.02em' }}>
          <a href="#research" style={{ padding: '7px 12px', borderRadius: 8, color: 'var(--text-dim)' }}>Research</a>
          <a href="#chat" style={{ padding: '7px 12px', borderRadius: 8, color: 'var(--text-dim)' }}>Chat</a>
          <a href="#models" style={{ padding: '7px 12px', borderRadius: 8, color: 'var(--text-dim)' }}>Models</a>
        </nav>
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ position: 'relative' }}>
            <button onClick={() => setAccentMenuOpen(!accentMenuOpen)} title="Change accent color" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: 38, height: 38, border: '1px solid var(--border)', background: 'var(--surface)', borderRadius: 999, cursor: 'pointer', transition: 'background .2s' }}>
              <span style={{ width: 14, height: 14, borderRadius: '50%', background: accent }} />
            </button>
            {accentMenuOpen && (
              <div style={{ position: 'absolute', top: '100%', right: 0, marginTop: 8, background: 'var(--surface)', border: '1px solid var(--border-strong)', borderRadius: 12, padding: 12, display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 8, boxShadow: 'var(--shadow)', zIndex: 100, animation: 'lp-pop .2s ease both' }}>
                {ACCENT_COLORS.map(c => (
                  <button key={c} onClick={() => { console.log('Selected accent color:', c); setAccent(c); setAccentMenuOpen(false); }} style={{ width: 24, height: 24, borderRadius: '50%', background: c, border: accent === c ? '2px solid var(--text)' : '1px solid rgba(0,0,0,0.1)', cursor: 'pointer', padding: 0 }} />
                ))}
              </div>
            )}
          </div>
          <button onClick={toggleTheme} title="Toggle theme" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: 38, height: 38, border: '1px solid var(--border)', background: 'var(--surface)', color: 'var(--text-dim)', borderRadius: 999, cursor: 'pointer' }}>
            {isDark ? (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>
            ) : (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>
            )}
          </button>
          <button onClick={goDashboard} className="lp-mono" style={{ display: 'flex', alignItems: 'center', gap: 8, height: 38, padding: '0 18px', border: 'none', borderRadius: 999, background: 'var(--accent)', color: '#fff', fontSize: 12.5, fontWeight: 500, cursor: 'pointer' }}>
            Sign in
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>
          </button>
        </div>
      </header>

      {/* ===== HERO ===== */}
      <section id="top" data-screen-label="Hero" style={{ position: 'relative', overflow: 'hidden' }}>
        <canvas ref={waveRef} style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', pointerEvents: 'none', zIndex: 0 }}></canvas>
        <div style={{ position: 'relative', zIndex: 1, maxWidth: 1080, margin: '0 auto', padding: 'clamp(56px,10vw,120px) clamp(20px,5vw,44px) clamp(40px,6vw,72px)', textAlign: 'center' }}>
          <div className="lp-mono" style={{ display: 'inline-flex', alignItems: 'center', gap: 9, fontSize: 11, letterSpacing: '.16em', textTransform: 'uppercase', color: 'var(--text-faint)', border: '1px solid var(--border)', background: 'var(--surface)', borderRadius: 999, padding: '7px 15px', marginBottom: 30, animation: 'lp-rise .5s ease both' }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--accent)' }}></span>Research + chat workspace
          </div>
          <h1 style={{ margin: '0 auto', maxWidth: '15ch', fontSize: 'clamp(42px,7vw,84px)', fontWeight: 300, lineHeight: 1.02, letterSpacing: '-.03em', textWrap: 'balance', animation: 'lp-rise .5s ease both .04s', animationFillMode: 'both' }}>
            Ask a hard question.<br />Get a <span style={{ fontStyle: 'italic', color: 'var(--accent)' }}>sourced</span> answer.
          </h1>
          <p style={{ margin: '26px auto 0', maxWidth: '56ch', fontSize: 'clamp(17px,2.2vw,21px)', fontWeight: 400, lineHeight: 1.6, color: 'var(--text)', textWrap: 'pretty', animation: 'lp-rise .5s ease both .1s' }}>
            Singularity turns one prompt into a long, cited research report — or a quick chat when you just need to think out loud. Bring your own model keys, and keep every source.
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, justifyContent: 'center', marginTop: 36, animation: 'lp-rise .5s ease both .16s' }}>
            <button onClick={goDashboard} className="lp-mono" style={{ display: 'flex', alignItems: 'center', gap: 9, height: 50, padding: '0 26px', border: 'none', borderRadius: 999, background: 'var(--accent)', color: '#fff', fontSize: 13.5, fontWeight: 500, cursor: 'pointer', boxShadow: 'var(--shadow-sm)' }}>
              Get started
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>
            </button>
            <a href="#research" className="lp-mono" style={{ display: 'flex', alignItems: 'center', gap: 9, height: 50, padding: '0 24px', border: '1px solid var(--border-strong)', borderRadius: 999, background: 'var(--surface)', color: 'var(--text)', fontSize: 13.5, fontWeight: 500 }}>
              See a sample report
            </a>
          </div>
          <div className="lp-mono" style={{ marginTop: 18, fontSize: 11.5, color: 'var(--text-faint)', animation: 'lp-rise .5s ease both .2s' }}>No credit card · Your keys, your usage</div>

          {/* composer mock */}
          <div style={{ maxWidth: 660, margin: 'clamp(44px,7vw,76px) auto 0', textAlign: 'left', animation: 'lp-rise .6s ease both .26s' }}>
            <div style={{ background: 'var(--surface)', border: '1px solid var(--border-strong)', borderRadius: 22, boxShadow: 'var(--shadow)', padding: '20px 20px 12px' }}>
              <div style={{ fontSize: 19, fontWeight: 300, lineHeight: 1.5, color: 'var(--text)', padding: '4px 4px 14px' }}>Compare solid-state and LFP battery cost curves through 2027, with sources.</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                <span className="lp-mono" style={{ display: 'flex', alignItems: 'center', gap: 7, height: 32, padding: '0 12px', border: '1px solid var(--border)', background: 'var(--surface-2)', borderRadius: 10, fontSize: 12, color: 'var(--text)' }}><span style={{ width: 7, height: 7, borderRadius: '50%', background: 'var(--accent)' }}></span>Research</span>
                <span className="lp-mono" style={{ display: 'flex', alignItems: 'center', gap: 7, height: 32, padding: '0 12px', border: '1px solid var(--border)', background: 'var(--surface-2)', borderRadius: 10, fontSize: 12, color: 'var(--text)' }}>High</span>
                <span className="lp-mono" style={{ display: 'flex', alignItems: 'center', gap: 7, height: 32, padding: '0 12px', border: '1px solid var(--border)', background: 'var(--surface-2)', borderRadius: 10, fontSize: 12, color: 'var(--text)' }}><span style={{ width: 8, height: 8, borderRadius: '50%', background: '#d97757' }}></span>Claude Sonnet 4.5</span>
                <span style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', justifyContent: 'center', width: 40, height: 40, borderRadius: 11, background: 'var(--accent)', color: '#fff' }}><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/></svg></span>
              </div>
            </div>
            <div className="lp-mono" style={{ textAlign: 'center', marginTop: 12, fontSize: 10.5, letterSpacing: '.04em', color: 'var(--text-faint)' }}>Enter to send · Shift+Enter for newline</div>
          </div>
        </div>
      </section>

      {/* ===== RESEARCH SECTION ===== */}
      <section id="research" ref={researchRef} data-screen-label="Research" style={{ position: 'relative', borderTop: '1px solid var(--border)', background: 'var(--surface-2)', height: '340vh' }}>
        <div style={{ position: 'sticky', top: 66, height: 'calc(100vh - 66px)', overflow: 'hidden', display: 'flex', alignItems: 'center' }}>
          <div style={{ maxWidth: 1120, width: '100%', margin: '0 auto', padding: '0 clamp(20px,5vw,44px)', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 'clamp(32px,5vw,64px)', alignItems: 'center' }}>
            {/* left */}
            <div>
              <div className="lp-mono" style={{ fontSize: 11, letterSpacing: '.16em', textTransform: 'uppercase', color: 'var(--accent-2)', marginBottom: 16 }}>Research mode</div>
              <h2 style={{ margin: 0, fontSize: 'clamp(30px,4vw,48px)', fontWeight: 300, lineHeight: 1.08, letterSpacing: '-.025em', textWrap: 'balance' }}>A report, <span style={{ fontStyle: 'italic' }}>not a paragraph.</span></h2>
              <p style={{ margin: '18px 0 0', fontSize: 17, fontWeight: 300, lineHeight: 1.66, color: 'var(--text-dim)', maxWidth: '44ch', textWrap: 'pretty' }}>
                Point Singularity at a topic and a pipeline of agents scopes, plans, researches inside a bounded workspace, checks its own work, and hands back a cited report. Scroll to watch it assemble.
              </p>
              <div style={{ marginTop: 34, maxWidth: 360 }}>
                <div style={{ height: 3, borderRadius: 99, background: 'var(--border)', overflow: 'hidden' }}>
                  <div style={{ height: '100%', borderRadius: 99, background: 'var(--accent)', width: `${Math.round(rp * 100)}%`, transition: 'width .08s linear' }}></div>
                </div>
                <div style={{ marginTop: 16, minHeight: 54 }}>
                  <div className="lp-mono" style={{ fontSize: 10.5, letterSpacing: '.1em', textTransform: 'uppercase', color: 'var(--text-faint)' }}>Phase {activeIdx + 1} of {n}</div>
                  <div style={{ fontSize: 20, fontWeight: 400, color: 'var(--text)', marginTop: 4 }}>System Active</div>
                </div>
              </div>
            </div>

            {/* right */}
            <div style={{ position: 'relative', minHeight: 600, display: 'flex', alignItems: 'center', justifyContent: 'center', width: '100%' }}>
               <AgentFlowchart progress={rp} />
            </div>
          </div>
        </div>
      </section>

      {/* ===== CHAT SECTION ===== */}
      <section id="chat" data-screen-label="Chat" style={{ borderTop: '1px solid var(--border)' }}>
        <div style={{ maxWidth: 1120, margin: '0 auto', padding: 'clamp(64px,9vw,104px) clamp(20px,5vw,44px)', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 'clamp(32px,5vw,64px)', alignItems: 'center' }}>
          <div className="reveal" style={{ background: 'var(--surface)', border: '1px solid var(--border-strong)', borderRadius: 18, boxShadow: 'var(--shadow)', padding: 'clamp(20px,3vw,30px)', display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', gap: 18, height: 435, overflow: 'hidden' }}>
            {demo.items.map((m, i) => {
              const user = m.role === 'user';
              return (
                <div key={i} style={{ alignSelf: user ? 'flex-end' : 'flex-start', maxWidth: user ? '82%' : '94%', animation: 'lp-pop .3s ease both' }}>
                  <div className="lp-mono" style={{ fontSize: 9.5, letterSpacing: '.1em', textTransform: 'uppercase', color: 'var(--text-faint)', marginBottom: 6, textAlign: user ? 'right' : 'left' }}>{user ? 'You' : 'Singularity'}</div>
                  <div style={{ ...(user ? { background: 'var(--accent-soft)', border: '1px solid var(--border)', borderRadius: '15px 15px 4px 15px', padding: '11px 14px', fontSize: 15.5, lineHeight: 1.5, color: 'var(--text)' } : { fontSize: 15.5, lineHeight: 1.62, color: 'var(--text)' }) }}>
                    {m.text}{m.streaming ? '▍' : ''}
                  </div>
                </div>
              );
            })}
            {demo.typing && (
              <div style={{ alignSelf: 'flex-start', maxWidth: '94%', animation: 'lp-pop .3s ease both' }}>
                <div className="lp-mono" style={{ fontSize: 9.5, letterSpacing: '.1em', textTransform: 'uppercase', color: 'var(--text-faint)', marginBottom: 6 }}>Singularity</div>
                <div style={{ display: 'inline-flex', alignItems: 'center', gap: 5, padding: '12px 15px' }}>
                  <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--text-dim)', animation: 'lp-dot 1.1s ease-in-out infinite' }}></span>
                  <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--text-dim)', animation: 'lp-dot 1.1s ease-in-out infinite .18s' }}></span>
                  <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--text-dim)', animation: 'lp-dot 1.1s ease-in-out infinite .36s' }}></span>
                </div>
              </div>
            )}
          </div>
          <div className="reveal" style={{ transitionDelay: '.12s' }}>
            <div className="lp-mono" style={{ fontSize: 11, letterSpacing: '.16em', textTransform: 'uppercase', color: 'var(--accent-2)', marginBottom: 16 }}>Chat mode</div>
            <h2 style={{ margin: 0, fontSize: 'clamp(32px,4.4vw,52px)', fontWeight: 300, lineHeight: 1.08, letterSpacing: '-.025em', textWrap: 'balance' }}>Or just <span style={{ fontStyle: 'italic' }}>talk it through.</span></h2>
            <p style={{ margin: '20px 0 0', fontSize: 18, fontWeight: 300, lineHeight: 1.68, color: 'var(--text-dim)', maxWidth: '46ch', textWrap: 'pretty' }}>
              Sometimes you don't need a document — you need a fast answer. Chat is quick back-and-forth on the same model picker, and any thread can graduate into a full sourced report the moment it gets serious.
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 2, marginTop: 30 }}>
              {/* Features skipped for brevity, but let's add them back as simplified blocks */}
              {[
                { title: 'Instant back-and-forth', body: 'Quick answers with no ceremony — the fastest way to think a problem through.' },
                { title: 'Promote to research', body: 'Turn any thread into a full sourced report the moment a question gets serious.' },
                { title: 'Any model, one picker', body: 'Swap between Claude, GPT-5, DeepSeek, Grok, or Groq without leaving the conversation.' }
              ].map((f, i) => (
                <div key={i} style={{ display: 'flex', gap: 14, padding: '16px 0', borderTop: '1px solid var(--border)' }}>
                  <span style={{ flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', width: 34, height: 34, border: '1px solid var(--border)', background: 'var(--surface)', borderRadius: 10, color: 'var(--accent-2)' }}>
                    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7"><circle cx="12" cy="12" r="9"/></svg>
                  </span>
                  <div>
                    <div style={{ fontSize: 16.5, fontWeight: 400, color: 'var(--text)' }}>{f.title}</div>
                    <div style={{ fontSize: 14.5, lineHeight: 1.55, color: 'var(--text-dim)', marginTop: 2 }}>{f.body}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ===== TERMINAL SECTION ===== */}
      <section id="terminal" data-screen-label="Terminal" style={{ borderTop: '1px solid var(--border)' }}>
        <div style={{ maxWidth: 1200, margin: '0 auto', padding: 'clamp(64px,9vw,104px) clamp(20px,5vw,44px)', display: 'flex', flexWrap: 'wrap', gap: 'clamp(32px,5vw,64px)', alignItems: 'center' }}>
          
          <div className="reveal" style={{ flex: '1 1 340px' }}>
            <div className="lp-mono" style={{ fontSize: 11, letterSpacing: '.16em', textTransform: 'uppercase', color: 'var(--accent-2)', marginBottom: 16 }}>Terminal mode</div>
            <h2 style={{ margin: 0, fontSize: 'clamp(32px,4.4vw,52px)', fontWeight: 300, lineHeight: 1.08, letterSpacing: '-.025em', textWrap: 'balance' }}>Singularity lives <span style={{ fontStyle: 'italic' }}>in your terminal.</span></h2>
            <p style={{ margin: '20px 0 0', fontSize: 18, fontWeight: 300, lineHeight: 1.68, color: 'var(--text-dim)', maxWidth: '46ch', textWrap: 'pretty' }}>
              Prefer the command line? Run <code style={{ background: 'var(--surface-2)', border: '1px solid var(--border)', padding: '3px 7px', borderRadius: 6, fontSize: 15 }}>npx singularity</code> to instantly bring your workspace into your terminal. All your keys, models, and research reports are immediately available via the CLI.
            </p>
          </div>

          <div className="reveal" style={{ flex: '1.4 1 480px', transitionDelay: '.12s', background: '#18181b', borderRadius: 12, overflow: 'hidden', boxShadow: '0 24px 80px rgba(0,0,0,0.5)', border: '1px solid rgba(255,255,255,0.1)' }}>
            <div style={{ background: '#27272a', padding: '12px 16px', display: 'flex', alignItems: 'center', gap: 8 }}>
              <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#ff5f56' }} />
              <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#ffbd2e' }} />
              <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#27c93f' }} />
            </div>
            <div className="lp-mono" style={{ padding: '24px', color: '#d4d4d4', fontSize: 12.5, lineHeight: 1.6, overflowX: 'auto' }}>
              <pre style={{ margin: '0 0 24px 0', color: 'var(--accent)', fontSize: '10px', lineHeight: 1.15, fontFamily: '"JetBrains Mono", "Courier New", Courier, monospace', whiteSpace: 'pre', letterSpacing: 0 }}>
{`███████╗██╗███╗   ██╗ ██████╗ ██╗   ██╗██╗      █████╗ ██████╗ ██╗████████╗██╗   ██╗
██╔════╝██║████╗  ██║██╔════╝ ██║   ██║██║     ██╔══██╗██╔══██╗██║╚══██╔══╝╚██╗ ██╔╝
███████╗██║██╔██╗ ██║██║  ███╗██║   ██║██║     ███████║██████╔╝██║   ██║    ╚████╔╝
╚════██║██║██║╚██╗██║██║   ██║██║   ██║██║     ██╔══██║██╔══██╗██║   ██║     ╚██╔╝
███████║██║██║ ╚████║╚██████╔╝╚██████╔╝███████╗██║  ██║██║  ██║██║   ██║      ██║
╚══════╝╚═╝╚═╝  ╚═══╝ ╚═════╝  ╚═════╝ ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝   ╚═╝      ╚═╝`}
              </pre>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {TERMINAL_COMMANDS.map((cmd, i) => (
                  <div key={i} className="reveal" style={{ display: 'flex', gap: 16, transitionDelay: `${0.2 + i * 0.06}s` }}>
                    <span style={{ color: '#4ec9b0', width: 75, flexShrink: 0 }}>{cmd.cmd}</span>
                    <span style={{ color: '#a1a1aa' }}>{cmd.desc}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ===== MODELS STRIP ===== */}
      <section id="models" style={{ borderTop: '1px solid var(--border)', background: 'var(--surface-2)' }}>
        <div style={{ maxWidth: 1120, margin: '0 auto', padding: 'clamp(52px,7vw,84px) clamp(20px,5vw,44px)', textAlign: 'center' }}>
          <div className="lp-mono" style={{ fontSize: 11, letterSpacing: '.16em', textTransform: 'uppercase', color: 'var(--text-faint)', marginBottom: 14 }}>Bring your own model</div>
          <h2 className="reveal" style={{ margin: '0 auto', maxWidth: '20ch', fontSize: 'clamp(26px,3.4vw,40px)', fontWeight: 300, lineHeight: 1.16, letterSpacing: '-.02em', textWrap: 'balance' }}>One workspace, every frontier model. Your keys stay yours.</h2>
          <div className="reveal" style={{ transitionDelay: '.12s', display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: 12, marginTop: 34 }}>
            {PROVIDERS.map((p, i) => (
              <div key={i} className="lp-mono" style={{ display: 'flex', alignItems: 'center', gap: 10, height: 44, padding: '0 18px', border: '1px solid var(--border)', background: 'var(--surface)', borderRadius: 999, fontSize: 13, color: 'var(--text)' }}>
                <span style={{ width: 20, height: 20, flexShrink: 0, opacity: .9, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <div style={{ width: '100%', height: '100%', backgroundColor: 'var(--accent)', WebkitMaskImage: `url(${p.logo})`, WebkitMaskSize: 'contain', WebkitMaskRepeat: 'no-repeat', WebkitMaskPosition: 'center', maskImage: `url(${p.logo})`, maskSize: 'contain', maskRepeat: 'no-repeat', maskPosition: 'center' }} />
                </span>
                {p.name}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ===== CTA BAND ===== */}
      <section style={{ borderTop: '1px solid var(--border)' }}>
        <div style={{ maxWidth: 1120, margin: '0 auto', padding: 'clamp(64px,9vw,110px) clamp(20px,5vw,44px)', textAlign: 'center' }}>
          <AppLogoMark width={44} height={44} style={{ display: 'block', margin: '0 auto 22px' }} />
          <h2 className="reveal" style={{ margin: '0 auto', maxWidth: '18ch', fontSize: 'clamp(34px,5vw,60px)', fontWeight: 300, lineHeight: 1.06, letterSpacing: '-.03em', textWrap: 'balance' }}>Intelligence emerges <span style={{ fontStyle: 'italic', color: 'var(--accent)' }}>at this point.</span></h2>
          <div className="reveal" style={{ transitionDelay: '.12s', marginTop: 34 }}>
            <button onClick={goDashboard} className="lp-mono" style={{ display: 'inline-flex', alignItems: 'center', gap: 9, height: 52, padding: '0 30px', border: 'none', borderRadius: 999, background: 'var(--accent)', color: '#fff', fontSize: 13.5, fontWeight: 500, cursor: 'pointer', boxShadow: 'var(--shadow-sm)' }}>
              Open your workspace
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>
            </button>
          </div>
        </div>
      </section>

      {/* ===== FOOTER ===== */}
      <footer data-screen-label="Footer" style={{ borderTop: '1px solid var(--border)', background: 'var(--surface)' }}>
        <div style={{ maxWidth: 1120, margin: '0 auto', padding: 'clamp(44px,6vw,68px) clamp(20px,5vw,44px)' }}>
          <div className="reveal" style={{ display: 'flex', flexWrap: 'wrap', gap: '48px 64px', justifyContent: 'space-between' }}>
            <div style={{ flex: '1 1 300px', maxWidth: '35ch' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
                <AppLogoMark width={26} height={26} />
                <span style={{ fontSize: 18, fontWeight: 500, letterSpacing: '-.01em' }}>Singularity</span>
              </div>
              <p style={{ margin: 0, fontSize: 14.5, fontStyle: 'italic', lineHeight: 1.6, color: 'var(--text-dim)' }}>Intelligence emerges at this point — a research and chat workspace on the models you already pay for.</p>
            </div>
            <div style={{ display: 'flex', gap: 64, flexWrap: 'wrap' }}>
              {FOOTER_COLS.map((col, i) => (
                <div key={i} style={{ minWidth: 140 }}>
                  <div className="lp-mono" style={{ fontSize: 10, letterSpacing: '.14em', textTransform: 'uppercase', color: 'var(--text-faint)', marginBottom: 14 }}>{col.title}</div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                    {col.links.map((l, j) => (
                      <a key={j} href={l.href} style={{ fontSize: 14.5, color: 'var(--text-dim)' }}>{l.label}</a>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="lp-mono" style={{ display: 'flex', flexWrap: 'wrap', gap: 14, alignItems: 'center', justifyContent: 'space-between', marginTop: 44, paddingTop: 22, borderTop: '1px solid var(--border)', fontSize: 11, color: 'var(--text-faint)' }}>
            <span>Singularity by <a href="https://github.com/hellonish" target="_blank" rel="noopener noreferrer">Nishant Sharma</a></span>
            <span style={{ fontStyle: 'italic', fontFamily: "'Newsreader', serif", fontSize: 13 }}>"I think, therefore I am." — René Descartes</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export const MODELS = [
  { group: 'Anthropic', dot: '#d97757', items: [ { id: 'claude-opus-4-1', name: 'Claude Opus 4.1' }, { id: 'claude-sonnet-4-5', name: 'Claude Sonnet 4.5' } ] },
  { group: 'OpenAI', dot: '#10a37f', items: [ { id: 'gpt-5', name: 'GPT-5' }, { id: 'gpt-5-mini', name: 'GPT-5 mini' } ] },
  { group: 'DeepSeek', dot: '#4d6bfe', items: [ { id: 'deepseek-v3', name: 'DeepSeek V3' }, { id: 'deepseek-r1', name: 'DeepSeek R1' } ] },
  { group: 'xAI', dot: '#c9ccd1', items: [ { id: 'grok-4', name: 'Grok 4' } ] },
  { group: 'Groq', dot: '#f55036', items: [ { id: 'llama-3.3-70b', name: 'Llama 3.3 70B' } ] },
];

export const PROVIDERS = [
  { id: 'anthropic', name: 'Anthropic', sub: 'Claude', dot: '#d97757', logo: '/logos/anthropic.svg', url: 'https://console.anthropic.com/settings/keys', prefix: 'sk-ant-…', blurb: 'Claude Opus & Sonnet — strongest long-form synthesis for Ultra research.', docHint: 'Tip: create a workspace key so usage is scoped per project.' },
  { id: 'openai', name: 'OpenAI', sub: 'GPT-5', dot: '#10a37f', logo: '/logos/openai.svg', url: 'https://platform.openai.com/api-keys', prefix: 'sk-…', blurb: 'GPT-5 family — fast general reasoning for Chat and Medium research.', docHint: 'Set a monthly usage limit in Billing to stay in budget.' },
  { id: 'deepseek', name: 'DeepSeek', sub: 'V3 · R1', dot: '#4d6bfe', logo: '/logos/deepseek.svg', url: 'https://platform.deepseek.com/api_keys', prefix: 'sk-…', blurb: 'DeepSeek R1 reasoning at low cost — great value for High-depth runs.', docHint: 'Add credit first; keys are inactive until the balance is funded.' },
  { id: 'grok', name: 'Grok', sub: 'xAI · Grok 4', dot: '#c9ccd1', logo: '/logos/grok.svg', url: 'https://console.x.ai', prefix: 'xai-…', blurb: 'Grok 4 with live signal — useful for fast, current-events research.', docHint: 'Create the key inside a Team to share it across seats.' },
  { id: 'groq', name: 'Groq', sub: 'Fast inference', dot: '#f55036', logo: '/logos/groq.svg', url: 'https://console.groq.com/keys', prefix: 'gsk_…', blurb: 'Groq LPU inference — the fastest tokens for Instant answers.', docHint: 'Free tier is rate-limited; upgrade for sustained Instant throughput.' },
  { id: 'openrouter', name: 'OpenRouter', sub: 'All models · one key', dot: '#6467f2', logo: '/logos/openrouter.svg', url: 'https://openrouter.ai/keys', prefix: 'sk-or-…', blurb: 'One key, every model — route across providers with automatic fallback.', docHint: 'Add credits or connect a provider key; set limits per key in the dashboard.' },
];

export const INTENSITIES = [
  { id: 'instant', name: 'Instant', bars: 1, desc: 'One quick pass — seconds.' },
  { id: 'medium', name: 'Medium', bars: 2, desc: 'Balanced multi-source — ~2 min.' },
  { id: 'high', name: 'High', bars: 3, desc: 'Deep retrieval — ~6 min.' },
  { id: 'ultra', name: 'Ultra', bars: 4, desc: 'Exhaustive synthesis — ~15 min.' },
];

// The user drives each step by interacting with the real UI (clicking Settings,
// choosing a provider, saving a key). `hint` is the tiny "do this now" line and
// `advanceOn` records which real action moves the tour forward.
export const OB_STEPS = [
  { target: 'menu-settings', title: 'Make Singularity your own', advanceOn: 'openSettings', hint: 'Click "Settings" to open your setup panel.', desc: 'Make Singularity your own — start by going to Settings.' },
  { target: 'providers', title: 'Model provider setup', advanceOn: 'pickProvider', hint: 'Open the dropdown and pick a provider — try Anthropic.', desc: 'You can set up any model provider here, with your own key.' },
  { target: 'keysetup', title: 'Add your key', advanceOn: 'saveKey', hint: 'Follow the steps, then paste your key and hit Save.', desc: 'Follow the steps to get your model key, then paste it in below.' },
  { target: 'composer', title: 'Send your first message', advanceOn: 'finish', hint: 'We typed a message for you — press Enter to send it.', desc: "Yay! You're all set! Send your first message to Singularity." },
];

// Prefilled first message that gets "typed" into the composer at the final step.
export const OB_STARTER_MESSAGE = 'Hi Singularity! Give me a 3-point overview of what you can help me with.';

export const REPORTS = [
  { id: 'r1', title: 'Solid-state battery supply chains and 2027 cost curves', time: '2h ago', chars: '48k chars', ver: 3, tier: 'ultra', chats: [ { id: 'c1', title: 'Supply chain risk' }, { id: 'c2', title: 'Cost sensitivity' }, { id: 'c3', title: 'Compare to LFP' } ] },
  { id: 'r2', title: 'Competitive landscape of open-weight reasoning models', time: 'Yesterday', chars: '31k chars', ver: 2, tier: 'high', chats: [ { id: 'c1', title: 'Licensing terms' }, { id: 'c2', title: 'Benchmark deltas' } ] },
  { id: 'r3', title: 'Regulatory outlook for stablecoin issuers in the EU', time: '2d ago', chars: '22k chars', ver: 1, tier: 'medium', chats: [ { id: 'c1', title: 'MiCA timeline' } ] },
  { id: 'r4', title: 'Fusion startups: funding, timelines, and technical risk', time: '4d ago', chars: '39k chars', ver: 2, tier: 'high', chats: [ { id: 'c1', title: 'Funding rounds' }, { id: 'c2', title: 'Net-energy claims' } ] },
  { id: 'r5', title: 'GLP-1 market: prescribers, payers, and supply', time: '1w ago', chars: '17k chars', ver: 1, tier: 'medium', chats: [ { id: 'c1', title: 'Payer coverage' } ] },
  { id: 'r6', title: 'Quick take — desalination cost per cubic meter', time: '1w ago', chars: '6k chars', ver: 1, tier: 'instant', chats: [ { id: 'c1', title: 'Energy cost driver' } ] },
];

export const STANDALONE_CHATS = [
  { id: 'sc1', title: 'Explain diffusion transformers simply' },
  { id: 'sc2', title: 'Summarize the Q3 earnings call' },
];

export const BLOCKS = [
  { type: 'lead', text: 'Solid-state cells are on track to undercut today’s lithium-ion packs on a $/kWh basis before the end of the decade, but the transition hinges on two fragile inputs: sulfide electrolyte supply and dry-room manufacturing capacity.' },
  { type: 'h2', text: 'Key findings' },
  { type: 'callout', label: 'Key finding', text: 'Projected pack cost falls ~45% between 2024 and 2027, crossing the $60/kWh line that makes solid-state competitive for mass-market EVs.' },
  { type: 'stats', items: [ { v: '$54', k: '/kWh by 2027', d: '−45% vs 2024', dc: 'var(--color-ok)' }, { v: '3.2×', k: 'energy density', d: 'vs Li-ion', dc: 'var(--color-text-dim)' }, { v: '2027', k: 'first GWh line', d: 'estimated', dc: 'var(--color-text-dim)' } ] },
  { type: 'h2', text: 'Cost trajectory to 2027' },
  { type: 'chart', title: 'Projected pack cost ($/kWh)', data: [ { label: '2024', v: 98 }, { label: '2025', v: 82 }, { label: '2026', v: 67 }, { label: '2027', v: 54 } ], caption: 'Blended cell + pack cost, base-case scenario. Source: internal model, BNEF inputs.' },
  { type: 'p', text: 'The steepest declines come from electrolyte yield improvements rather than cathode chemistry, which is already near its practical floor. Capacity additions in South Korea and Japan account for most of the 2026–2027 step-down.' },
  { type: 'h2', text: 'Supplier comparison' },
  { type: 'table', head: ['Supplier', 'Region', 'Capacity', 'Status'], rows: [ ['QuantumScape', 'US', '4 GWh', 'Pilot'], ['Samsung SDI', 'KR', '12 GWh', 'Scaling'], ['Toyota / Idemitsu', 'JP', '9 GWh', 'Announced'], ['ProLogium', 'TW', '7 GWh', 'Scaling'] ] },
  { type: 'image', caption: 'Figure 1 — sulfide-electrolyte cell architecture' },
  { type: 'h2', text: 'Outlook' },
  { type: 'p', text: 'Base case assumes no major electrolyte shortage. A supply crunch in lithium sulfide would push parity out by roughly 18 months and keep early volumes locked to premium vehicles.' },
  { type: 'quote', text: 'Whoever secures sulfide electrolyte at scale first will set the pack-cost floor for the rest of the decade.', cite: 'Internal synthesis · 42 sources' },
  { type: 'h2', text: 'Reference list' },
  { type: 'refs', items: [ { k: 'BNEF24', t: 'Battery Price Survey 2024.', u: 'bnef.com', href: 'https://about.bnef.com' }, { k: 'SDI25', t: 'Samsung SDI capacity roadmap, Q1 2025.', u: 'samsungsdi.com', href: 'https://samsungsdi.com' }, { k: 'QS24', t: 'QuantumScape shareholder letter, 2024.', u: 'quantumscape.com', href: 'https://quantumscape.com' } ] },
];

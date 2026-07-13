import React from "react";

function cn(...classes: (string | undefined | null | false)[]) {
  return classes.filter(Boolean).join(" ");
}

export type FlowchartProps = {
  progress: number; // 0.0 to 1.0
};

export function AgentFlowchart({ progress }: FlowchartProps) {
  const n = 8;
  const activeStep = Math.min(n - 1, Math.max(0, Math.floor(progress * n)));
  const isActive = (stepIndex: number) => activeStep >= stepIndex;

  const ShapeNode = ({
    x,
    y,
    w,
    h,
    title,
    caption,
    active,
    glowing = false,
    children,
  }: {
    x: number;
    y: number;
    w: number;
    h: number;
    title: string;
    caption?: string;
    active: boolean;
    glowing?: boolean;
    children?: React.ReactNode;
  }) => {
    const topBg = active ? 'var(--surface)' : 'var(--surface-2)';
    const topBorder = active ? 'var(--accent)' : 'var(--border)';

    return (
      <div className="absolute transition-all duration-500" style={{ left: x, top: y, width: w, height: h, zIndex: active ? 10 : 1 }}>
        <div className="absolute inset-0 flex flex-col items-center justify-center p-3 text-center transition-all duration-500 shadow-sm" style={{
          background: topBg, border: `1.5px solid ${topBorder}`,
          boxShadow: (active && glowing) ? '0 0 40px var(--accent-soft)' : '0 2px 10px rgba(0,0,0,0.02)',
        }}>
          <div className="font-medium text-[14px] leading-snug" style={{ color: 'var(--text)' }}>{title}</div>
          {caption && <div className="italic text-[11px] mt-1 opacity-80" style={{ color: 'var(--text-dim)' }}>{caption}</div>}
          {children}
        </div>
      </div>
    );
  };

  // Flow animation style
  const flowStyle = `
    @keyframes lp-flow-dash {
      to { stroke-dashoffset: -20; }
    }
    .flow-line {
      stroke-dasharray: 4 6;
      animation: lp-flow-dash 1s linear infinite;
    }
  `;

  return (
    <div className="relative w-full h-[760px] flex items-center justify-center overflow-visible">
      <style>{flowStyle}</style>
      
      <div className="relative" style={{ width: 600, height: 680 }}>
        {/* BACKGROUND SVG for streams (drawn on the 2D plane behind the 3D blocks) */}
        <svg className="absolute inset-0 w-full h-full overflow-visible z-0">
          <g fill="none" strokeWidth="2.5" className="transition-colors duration-500">
            {/* Trunk */}
            <path d="M 230 60 L 230 100" stroke={isActive(1) ? 'var(--accent)' : 'var(--border)'} className={isActive(1) ? "flow-line" : ""} />
            <path d="M 230 160 L 230 200" stroke={isActive(2) ? 'var(--accent)' : 'var(--border)'} className={isActive(2) ? "flow-line" : ""} />
            <path d="M 230 260 L 230 280" stroke={isActive(3) ? 'var(--accent)' : 'var(--border)'} className={isActive(3) ? "flow-line" : ""} />
            
            {/* Split to Planners */}
            <path d="M 70 280 L 390 280" stroke={isActive(3) ? 'var(--accent)' : 'var(--border)'} className={isActive(3) ? "flow-line" : ""} />
            <path d="M 70 280 L 70 300" stroke={isActive(3) ? 'var(--accent)' : 'var(--border)'} className={isActive(3) ? "flow-line" : ""} />
            <path d="M 230 280 L 230 300" stroke={isActive(3) ? 'var(--accent)' : 'var(--border)'} className={isActive(3) ? "flow-line" : ""} />
            <path d="M 390 280 L 390 300" stroke={isActive(3) ? 'var(--accent)' : 'var(--border)'} className={isActive(3) ? "flow-line" : ""} />

            {/* Merge Planners */}
            <path d="M 70 360 L 70 380" stroke={isActive(4) ? 'var(--accent)' : 'var(--border)'} className={isActive(4) ? "flow-line" : ""} />
            <path d="M 230 360 L 230 380" stroke={isActive(4) ? 'var(--accent)' : 'var(--border)'} className={isActive(4) ? "flow-line" : ""} />
            <path d="M 390 360 L 390 380" stroke={isActive(4) ? 'var(--accent)' : 'var(--border)'} className={isActive(4) ? "flow-line" : ""} />
            <path d="M 70 380 L 390 380" stroke={isActive(4) ? 'var(--accent)' : 'var(--border)'} className={isActive(4) ? "flow-line" : ""} />
            
            <path d="M 230 380 L 230 400" stroke={isActive(4) ? 'var(--accent)' : 'var(--border)'} className={isActive(4) ? "flow-line" : ""} />
            <path d="M 230 460 L 230 480" stroke={isActive(5) ? 'var(--accent)' : 'var(--border)'} className={isActive(5) ? "flow-line" : ""} />

            {/* Split to Agents */}
            <path d="M 70 480 L 390 480" stroke={isActive(5) ? 'var(--accent)' : 'var(--border)'} className={isActive(5) ? "flow-line" : ""} />
            <path d="M 70 480 L 70 500" stroke={isActive(5) ? 'var(--accent)' : 'var(--border)'} className={isActive(5) ? "flow-line" : ""} />
            <path d="M 230 480 L 230 500" stroke={isActive(5) ? 'var(--accent)' : 'var(--border)'} className={isActive(5) ? "flow-line" : ""} />
            <path d="M 390 480 L 390 500" stroke={isActive(5) ? 'var(--accent)' : 'var(--border)'} className={isActive(5) ? "flow-line" : ""} />

            {/* Merge Agents */}
            <path d="M 70 600 L 70 620" stroke={isActive(7) ? 'var(--accent)' : 'var(--border)'} className={isActive(7) ? "flow-line" : ""} />
            <path d="M 230 600 L 230 620" stroke={isActive(7) ? 'var(--accent)' : 'var(--border)'} className={isActive(7) ? "flow-line" : ""} />
            <path d="M 390 600 L 390 620" stroke={isActive(7) ? 'var(--accent)' : 'var(--border)'} className={isActive(7) ? "flow-line" : ""} />
            <path d="M 70 620 L 390 620" stroke={isActive(7) ? 'var(--accent)' : 'var(--border)'} className={isActive(7) ? "flow-line" : ""} />
            
            <path d="M 230 620 L 230 640" stroke={isActive(7) ? 'var(--accent)' : 'var(--border)'} className={isActive(7) ? "flow-line" : ""} />

            {/* QA Loop */}
            <path 
              d="M 450 534 L 480 534" 
              stroke={isActive(6) ? 'var(--warn)' : 'var(--border)'} 
              className={isActive(6) ? "flow-line" : ""} 
              markerEnd={isActive(6) ? "url(#arrowWarn)" : "url(#arrowDim)"}
            />
            <path 
              d="M 480 566 L 450 566" 
              stroke={isActive(6) ? 'var(--warn)' : 'var(--border)'} 
              className={isActive(6) ? "flow-line" : ""} 
              markerEnd={isActive(6) ? "url(#arrowWarn)" : "url(#arrowDim)"}
            />
          </g>
          <defs>
            <marker id="arrowWarn" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="6" markerHeight="6" orient="auto">
              <path d="M0,0 L10,5 L0,10 z" fill="var(--warn)" />
            </marker>
            <marker id="arrowDim" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="6" markerHeight="6" orient="auto">
              <path d="M0,0 L10,5 L0,10 z" fill="var(--border)" />
            </marker>
          </defs>
        </svg>

        {/* --- 2D NODES --- */}
        <ShapeNode x={100} y={0} w={260} h={60} title="Problem Statement" caption="What you asked" active={isActive(0)} />
        <ShapeNode x={100} y={100} w={260} h={60} title="Scoping Agent" caption="Clarifies the objective" active={isActive(1)} />
        <ShapeNode x={100} y={200} w={260} h={60} title="Research Lead" caption="Manages execution" active={isActive(2)} />

        {/* Planners */}
        <ShapeNode x={10} y={300} w={120} h={60} title="Planner A" caption="Workstream 1" active={isActive(3)} />
        <ShapeNode x={170} y={300} w={120} h={60} title="Planner B" caption="Workstream 2" active={isActive(3)} />
        <ShapeNode x={330} y={300} w={120} h={60} title="Planner C" caption="Workstream 3" active={isActive(3)} />

        <ShapeNode x={100} y={400} w={260} h={60} title="Dispatch Engine" caption="Spins up environments" active={isActive(4)} />

        {/* Agents */}
        {[10, 170, 330].map((x, i) => (
          <ShapeNode key={i} x={x} y={500} w={120} h={100} title={`Agent ${i + 1}`} active={isActive(5)}>
            <div className="mt-2 flex flex-col gap-1.5 w-full">
              <div className="flex justify-center items-center gap-1.5 rounded-sm bg-[var(--surface-3)] p-1 border border-[var(--border)] w-full shadow-sm">
                <img src="/reference/container.svg" alt="" className="w-3 h-3 opacity-80" />
                <span className="lp-mono text-[8px] text-[var(--text-dim)] uppercase tracking-widest">Container</span>
              </div>
              <div className="flex justify-center items-center gap-1.5 rounded-sm bg-[var(--surface-3)] p-1 border border-[var(--border)] w-full shadow-sm">
                <img src="/reference/sandbox.svg" alt="" className="w-3 h-3 opacity-80" />
                <span className="lp-mono text-[8px] text-[var(--text-dim)] uppercase tracking-widest">Sandbox</span>
              </div>
            </div>
          </ShapeNode>
        ))}

        {/* QA Agent */}
        <ShapeNode x={480} y={500} w={120} h={100} title="QA Agent" caption="Sits outside loop" active={isActive(6)}>
          <div className="absolute -top-3 -right-3 bg-[var(--warn)] text-white text-[9px] px-2 py-0.5 font-mono uppercase tracking-widest shadow-md">
            Review
          </div>
        </ShapeNode>

        {/* Writer Agent */}
        <ShapeNode x={100} y={640} w={260} h={60} title="Writer Agent" caption="Report formation" active={isActive(7)} glowing={true} />
      </div>
    </div>
  );
}

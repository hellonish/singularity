import React from "react";

type AppLogoMarkProps = {
  className?: string;
  style?: React.CSSProperties;
  width?: number | string;
  height?: number | string;
};

export function AppLogoMark({ className, style, width = 48, height = 48 }: AppLogoMarkProps) {
  return (
    <svg 
      width={width} 
      height={height} 
      viewBox="0 0 64 64" 
      fill="none" 
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      style={{ color: 'var(--text)', ...style }}
    >
      <defs>
        <mask id="engine-void">
          <rect width="64" height="64" fill="white"/>
          <circle cx="32" cy="32" r="12" fill="black"/>
          <path d="M 28 0 L 36 0 L 32 32 Z" fill="black"/>
          <path d="M 28 64 L 36 64 L 32 32 Z" fill="black"/>
          <path d="M 0 28 L 0 36 L 32 32 Z" fill="black"/>
          <path d="M 64 28 L 64 36 L 32 32 Z" fill="black"/>
          <path d="M 0 0 L 16 0 L 32 32 Z" fill="black"/>
          <path d="M 64 64 L 48 64 L 32 32 Z" fill="black"/>
          <path d="M 64 0 L 64 16 L 32 32 Z" fill="black"/>
          <path d="M 0 64 L 0 48 L 32 32 Z" fill="black"/>
        </mask>
      </defs>
      <circle cx="32" cy="32" r="30" fill="currentColor" mask="url(#engine-void)"/>
      <circle cx="32" cy="32" r="4" fill="currentColor"/>
    </svg>
  );
}

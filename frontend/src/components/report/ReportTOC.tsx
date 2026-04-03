"use client";

import { useEffect, useRef, useState } from "react";
import type { TOCEntry } from "./ReportViewer";

interface ReportTOCProps {
  entries: TOCEntry[];
}

export function ReportTOC({ entries }: ReportTOCProps) {
  const [activeId, setActiveId] = useState<string>("");

  useEffect(() => {
    if (entries.length === 0) return;
    const headingEls = entries
      .map((e) => document.getElementById(e.id))
      .filter(Boolean) as HTMLElement[];

    const observer = new IntersectionObserver(
      (obs) => {
        obs.forEach((entry) => {
          if (entry.isIntersecting) setActiveId(entry.target.id);
        });
      },
      { rootMargin: "-20% 0px -70% 0px" }
    );
    headingEls.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, [entries]);

  if (entries.length < 3) return null;

  return (
    <nav className="toc-root" aria-label="Table of contents">
      <div className="toc-label">Contents</div>
      <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
        {entries.map((entry) => (
          <li
            key={entry.id}
            className={`toc-item ${entry.level === 3 ? "toc-h3" : "toc-h2"} ${activeId === entry.id ? "toc-active" : ""}`}
          >
            <a
              href={`#${entry.id}`}
              title={entry.text}
              onClick={(e) => {
                e.preventDefault();
                document.getElementById(entry.id)?.scrollIntoView({ behavior: "smooth" });
              }}
            >
              {entry.text}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}

from __future__ import annotations

from .document import (
    ChartBlock,
    DocumentSection,
    HighlightBlock,
    MathBlock,
    ParagraphBlock,
    ResearchDocument,
    StatsBlock,
    TableBlock,
)


def to_markdown(document: ResearchDocument) -> str:
    """Loss-aware export for clients that only support Markdown."""
    parts = [f"# {document.title}", f"**Query:** {document.query}"]
    for section in document.sections:
        parts.append(_section(section, 2))
    if document.limitations:
        parts.append("## Limitations\n\n" + "\n".join(f"- {item}" for item in document.limitations))
    if document.references:
        refs = ["## Reference List"]
        refs.extend(f"- **{ref.tag}** [{ref.name}]({ref.url})" for ref in document.references)
        parts.append("\n".join(refs))
    return "\n\n".join(parts).strip() + "\n"


def _section(section: DocumentSection, level: int) -> str:
    heading = "#" * min(level, 6)
    parts = [f"{heading} {section.title}"]
    for block in section.blocks:
        if isinstance(block, ParagraphBlock):
            parts.append(_with_refs(block.text, block.reference_ids))
        elif isinstance(block, HighlightBlock):
            parts.append(f"> **{block.title}:** {_with_refs(block.body, block.reference_ids)}")
        elif isinstance(block, MathBlock):
            parts.append((f"$$\n{block.latex}\n$$" if block.display else f"${block.latex}$"))
        elif isinstance(block, StatsBlock):
            parts.append("\n".join(f"**{item.label}:** {item.value} {_refs(item.reference_ids)}" for item in block.items))
        elif isinstance(block, ChartBlock):
            parts.append(_chart_table(block))
        elif isinstance(block, TableBlock):
            parts.append(_table(block))
    for child in section.children:
        parts.append(_section(child, level + 1))
    return "\n\n".join(parts)


def _refs(ids: list[str]) -> str:
    return " ".join(f"[{item}]" for item in ids)


def _with_refs(text: str, ids: list[str]) -> str:
    suffix = _refs(ids)
    return f"{text} {suffix}".strip()


def _chart_table(block: ChartBlock) -> str:
    rows = [f"### {block.title}", f"| Label | Value |", "|---|---:|"]
    rows.extend(f"| {point.label} | {point.value:g} {block.unit} {_refs(point.reference_ids)} |" for point in block.points)
    return "\n".join(rows)


def _table(block: TableBlock) -> str:
    rows = ["| " + " | ".join(block.columns) + " |", "| " + " | ".join("---" for _ in block.columns) + " |"]
    rows.extend("| " + " | ".join(row) + " |" for row in block.rows)
    return "\n".join(rows)


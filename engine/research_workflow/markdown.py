from __future__ import annotations

from urllib.parse import urlsplit

from .document import (
    ChartBlock,
    DocumentSection,
    HighlightBlock,
    MathBlock,
    ParagraphBlock,
    ReferenceTag,
    ResearchDocument,
    StatsBlock,
    TableBlock,
)


def to_markdown(document: ResearchDocument) -> str:
    """Loss-aware export for clients that only support Markdown."""
    refs = {ref.tag: ref for ref in document.references}
    parts = [f"# {document.title}", f"**Query:** {document.query}"]
    for section in document.sections:
        parts.append(_section(section, 2, refs))
    if document.limitations:
        parts.append("## Limitations\n\n" + "\n".join(f"- {item}" for item in document.limitations))
    if document.references:
        lines = ["## Reference List"]
        lines.extend(f"- **{reference_label(ref)}** [{ref.name}]({ref.url})" for ref in document.references)
        parts.append("\n".join(lines))
    return "\n\n".join(parts).strip() + "\n"


def reference_label(ref: ReferenceTag) -> str:
    """The website name shown to the reader, e.g. ``arxiv.org`` — never ``www``."""
    host = urlsplit(ref.url).hostname or ref.tag
    if host.startswith("www."):
        host = host[len("www."):]
    return host


def _section(section: DocumentSection, level: int, refs: dict[str, ReferenceTag]) -> str:
    heading = "#" * min(level, 6)
    parts = [f"{heading} {section.title}"]
    for block in section.blocks:
        if isinstance(block, ParagraphBlock):
            parts.append(_with_refs(block.text, block.reference_ids, refs))
        elif isinstance(block, HighlightBlock):
            parts.append(f"> **{block.title}:** {_with_refs(block.body, block.reference_ids, refs)}")
        elif isinstance(block, MathBlock):
            parts.append((f"$$\n{block.latex}\n$$" if block.display else f"${block.latex}$"))
        elif isinstance(block, StatsBlock):
            parts.append("\n".join(f"**{item.label}:** {item.value} {_refs(item.reference_ids, refs)}" for item in block.items))
        elif isinstance(block, ChartBlock):
            parts.append(_chart_table(block, refs))
        elif isinstance(block, TableBlock):
            parts.append(_table(block))
    for child in section.children:
        parts.append(_section(child, level + 1, refs))
    return "\n\n".join(parts)


def _ref_link(ref_id: str, refs: dict[str, ReferenceTag]) -> str:
    """Render one inline citation as a hyperlink whose text is the website name."""
    ref = refs.get(ref_id)
    if ref is None:
        return f"[{ref_id}]"
    return f"[{reference_label(ref)}]({ref.url})"


def _refs(ids: list[str], refs: dict[str, ReferenceTag]) -> str:
    return " ".join(_ref_link(item, refs) for item in ids)


def _with_refs(text: str, ids: list[str], refs: dict[str, ReferenceTag]) -> str:
    suffix = _refs(ids, refs)
    return f"{text} {suffix}".strip()


def _chart_table(block: ChartBlock, refs: dict[str, ReferenceTag]) -> str:
    rows = [f"### {block.title}", f"| Label | Value |", "|---|---:|"]
    rows.extend(f"| {point.label} | {point.value:g} {block.unit} {_refs(point.reference_ids, refs)} |" for point in block.points)
    return "\n".join(rows)


def _table(block: TableBlock) -> str:
    rows = ["| " + " | ".join(block.columns) + " |", "| " + " | ".join("---" for _ in block.columns) + " |"]
    rows.extend("| " + " | ".join(row) + " |" for row in block.rows)
    return "\n".join(rows)

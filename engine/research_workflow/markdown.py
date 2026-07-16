from __future__ import annotations

import re
from html import escape
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
    validate_document,
)

# The researcher node numbers its evidence as ``SOURCE 1``/``SOURCE 2`` so the
# model can map claims to inputs while it drafts. Those tokens are an internal
# scaffold, never a citation the reader should see — every real citation becomes
# an inline hyperlink. Strip any that leak into prose.
_SOURCE_TOKEN = re.compile(r"\(?\s*\bSOURCES?\s*\d+(?:\s*(?:,|and|&|-|–|to)\s*\d+)*\s*\)?", re.IGNORECASE)

# Field separators for the enriched inline citation payload. A single ``<cite>``
# carries every exact link that shares its host: links are joined by ``||`` and
# each link's ``url``/``title`` by ``|``.
_LINK_FIELD_SEP = "|"
_LINK_SEP = "||"


def strip_source_tokens(text: str) -> str:
    """Remove leftover ``SOURCE N`` scaffolding tokens from reader-facing prose."""
    without = _SOURCE_TOKEN.sub("", text)
    # Removing a mid-sentence "(SOURCE 1)" can strand a space before the
    # following punctuation ("SQLite , and"). Reflow whitespace so the prose
    # reads as if the token were never there.
    without = re.sub(r"\s+([,.;:!?])", r"\1", without)
    return re.sub(r"\s{2,}", " ", without).strip()


def to_markdown(document: ResearchDocument) -> str:
    """Loss-aware export for clients that only support Markdown."""
    # Keep every export behind the same completeness invariant as the writer.
    # This protects persisted reports even if a future workflow collaborator
    # returns an unvalidated ResearchDocument.
    document = validate_document(document)
    refs = {ref.tag: ref for ref in document.references}
    parts = [f"# {document.title}", f"**Query:** {document.query}"]
    for section in document.sections:
        parts.append(_section(section, 2, refs))
    if document.limitations:
        parts.append("## Limitations\n\n" + "\n".join(f"- {item}" for item in document.limitations))
    if document.references:
        parts.append(_reference_list(document.references))
    return "\n\n".join(parts).strip() + "\n"


def reference_label(ref: ReferenceTag) -> str:
    """The website name shown to the reader, e.g. ``arxiv.org`` — never ``www``."""
    return host_label(ref.url) or ref.tag


def host_label(url: str) -> str:
    """Bare hostname for ``url`` with any leading ``www.`` removed."""
    host = urlsplit(url).hostname or ""
    if host.startswith("www."):
        host = host[len("www."):]
    return host


def _reference_list(references: list[ReferenceTag]) -> str:
    """Reference list deduped by host: one line per host, exact links nested.

    A project that cites four GitHub pages should surface ``github.com`` once,
    not four identical rows. Each host's exact URLs become sub-bullets so a
    plain-Markdown reader still reaches every source.
    """
    grouped = _group_by_host(references)
    lines = ["## Reference List"]
    for host, refs in grouped:
        lines.append(f"- **{host}**")
        for ref in refs:
            title = ref.title or ref.name
            lines.append(f"    - [{title}]({ref.url})")
    return "\n".join(lines)


def _group_by_host(refs: list[ReferenceTag]) -> list[tuple[str, list[ReferenceTag]]]:
    """Group references by host, preserving first-seen order of both host and ref.

    Two tags pointing at the same exact URL collapse to one entry; distinct URLs
    on the same host stay separate rows under a single host heading.
    """
    order: list[str] = []
    groups: dict[str, list[ReferenceTag]] = {}
    seen_urls: dict[str, set[str]] = {}
    for ref in refs:
        host = host_label(ref.url) or ref.tag
        if host not in groups:
            order.append(host)
            groups[host] = []
            seen_urls[host] = set()
        if ref.url in seen_urls[host]:
            continue
        seen_urls[host].add(ref.url)
        groups[host].append(ref)
    return [(host, groups[host]) for host in order]


def _cite(ids: list[str], refs: dict[str, ReferenceTag]) -> str:
    """Render a block's citations as one enrichable ``<cite>`` element per host.

    A paragraph citing several pages on the same site collapses to a single host
    chip (``github.com``) carrying every exact link, so the reader never sees the
    same identifier repeated. The frontend reads ``data-host``/``data-links`` to
    show the exact URLs on hover; plain-Markdown clients see the host text.
    """
    resolved = [refs[i] for i in ids if i in refs]
    if not resolved:
        return ""
    elements: list[str] = []
    for host, group in _group_by_host(resolved):
        payload = _LINK_SEP.join(
            f"{escape(ref.url, quote=True)}{_LINK_FIELD_SEP}{escape(ref.title or ref.name, quote=True)}"
            for ref in group
        )
        elements.append(
            f'<cite data-host="{escape(host, quote=True)}" data-links="{payload}">{escape(host)}</cite>'
        )
    return " ".join(elements)


def _section(section: DocumentSection, level: int, refs: dict[str, ReferenceTag]) -> str:
    heading = "#" * min(level, 6)
    parts = [f"{heading} {section.title}"]
    for block in section.blocks:
        if isinstance(block, ParagraphBlock):
            parts.append(_with_refs(strip_source_tokens(block.text), block.reference_ids, refs))
        elif isinstance(block, HighlightBlock):
            parts.append(f"> **{block.title}:** {_with_refs(strip_source_tokens(block.body), block.reference_ids, refs)}")
        elif isinstance(block, MathBlock):
            parts.append((f"$$\n{block.latex}\n$$" if block.display else f"${block.latex}$"))
        elif isinstance(block, StatsBlock):
            parts.append("\n".join(f"**{item.label}:** {item.value} {_cite(item.reference_ids, refs)}".rstrip() for item in block.items))
        elif isinstance(block, ChartBlock):
            parts.append(_chart_table(block, refs))
        elif isinstance(block, TableBlock):
            parts.append(_table(block))
    for child in section.children:
        parts.append(_section(child, level + 1, refs))
    return "\n\n".join(parts)


def _with_refs(text: str, ids: list[str], refs: dict[str, ReferenceTag]) -> str:
    suffix = _cite(ids, refs)
    return f"{text} {suffix}".strip()


def _chart_table(block: ChartBlock, refs: dict[str, ReferenceTag]) -> str:
    rows = [f"### {block.title}", f"| Label | Value |", "|---|---:|"]
    rows.extend(f"| {point.label} | {point.value:g} {block.unit} {_cite(point.reference_ids, refs)} |" for point in block.points)
    return "\n".join(rows)


def _table(block: TableBlock) -> str:
    rows = ["| " + " | ".join(block.columns) + " |", "| " + " | ".join("---" for _ in block.columns) + " |"]
    rows.extend("| " + " | ".join(row) + " |" for row in block.rows)
    return "\n".join(rows)

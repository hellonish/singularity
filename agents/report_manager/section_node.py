"""
SectionNode — data model for a single node in the report section tree.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SectionNode:
    node_id:      str
    parent_id:    str | None
    level:        int
    title:        str
    description:  str
    section_type: str          # root | chapter | section | subsection
    children:     list["SectionNode"] = field(default_factory=list, repr=False)

    # Set by workers after execution
    content:      str = ""
    word_count:   int = 0
    citations:    list[str] = field(default_factory=list)
    source_map:   dict = field(default_factory=dict)  # citation_id → {title, url}

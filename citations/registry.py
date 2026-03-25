"""
CitationRegistry — assigns stable [AuthorYYYY] IDs to every source found during
a research run.  Shared via ExecutionContext; all retrieval skills register here;
all analysis and output skills reference sources by citation_id only.
"""
import re
from dataclasses import dataclass, field


def _year(date: str | None) -> str | None:
    """Extract the 4-digit year from any date-ish string."""
    if not date:
        return None
    m = re.match(r"(\d{4})", str(date))
    return m.group(1) if m else None


@dataclass
class CitationRecord:
    citation_id:       str          # e.g. "[Smith2024]"
    title:             str
    authors:           list[str]
    year:              str | None
    url:               str
    source_type:       str          # matches SourceType literals
    credibility_base:  float
    registered_by:     str          # skill name that found this source
    registered_at_slot: str         # output_slot of the node that registered it


class CitationRegistry:
    """
    Thread-safe in-process registry of all sources accumulated during a run.

    Usage in a retrieval skill:
        cid = ctx.citation_registry.register(src_dict, "web_search", node.output_slot)
        src_dict["citation_id"] = cid
    """

    def __init__(self) -> None:
        self._records:  dict[str, CitationRecord] = {}
        self._by_slot:  dict[str, list[str]]      = {}   # slot → [citation_id]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register(self, source: dict, registered_by: str, output_slot: str) -> str:
        """
        Register a source dict (as returned by any tool) and return its citation_id.
        Duplicate registrations (same URL) return the existing id without overwriting.
        """
        url = source.get("url", "")
        existing = self._by_url(url)
        if existing:
            return existing

        cid = self._make_id(source)
        # Accept either "year" or "date" key from tool results
        year_raw = source.get("year") or source.get("date")
        self._records[cid] = CitationRecord(
            citation_id        = cid,
            title              = source.get("title", ""),
            authors            = list(source.get("authors") or []),
            year               = _year(str(year_raw)) if year_raw else None,
            url                = url,
            source_type        = source.get("source_type", "web"),
            credibility_base   = float(source.get("credibility_base", 0.0)),
            registered_by      = registered_by,
            registered_at_slot = output_slot,
        )
        self._by_slot.setdefault(output_slot, []).append(cid)
        return cid

    def get(self, citation_id: str) -> CitationRecord | None:
        return self._records.get(citation_id)

    def all(self) -> list[CitationRecord]:
        return list(self._records.values())

    def by_slot(self, output_slot: str) -> list[CitationRecord]:
        return [
            self._records[cid]
            for cid in self._by_slot.get(output_slot, [])
            if cid in self._records
        ]

    def format_bibliography(self, style: str = "APA", ids: list[str] | None = None) -> str:
        """Render a Markdown bibliography string for the requested citation_ids (all if None)."""
        records = [
            self._records[i]
            for i in (ids if ids is not None else list(self._records))
            if i in self._records
        ]
        if style == "APA":
            return "\n\n".join(self._apa(r) for r in records)
        if style == "IEEE":
            return "\n\n".join(self._ieee(i, r) for i, r in enumerate(records, 1))
        if style == "Vancouver":
            return "\n\n".join(self._vancouver(i, r) for i, r in enumerate(records, 1))
        # Default: one entry per paragraph with clickable URL on its own line
        return "\n\n".join(
            f"**{r.citation_id}** {r.title}\n{self._md_url(r.url)}"
            for r in records
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _by_url(self, url: str) -> str | None:
        """Return existing citation_id if this URL is already registered."""
        if not url:
            return None
        for cid, rec in self._records.items():
            if rec.url == url:
                return cid
        return None

    def _make_id(self, source: dict) -> str:
        """Generate a collision-resistant [Surname|TitleCamel + Year] id."""
        authors = source.get("authors") or []
        year_raw = source.get("year") or source.get("date")
        year    = (_year(str(year_raw)) if year_raw else None) or "ND"

        if authors:
            first_author = str(authors[0])
            if "," in first_author:
                # "Last, First" format — surname is before the comma
                surname = first_author.split(",")[0].strip()
            else:
                # "First Last" format — surname is the last token
                tokens  = [t for t in first_author.split() if t]
                surname = tokens[-1] if tokens else first_author
        else:
            # First 3 meaningful words of the title, CamelCased
            words   = re.findall(r"[A-Za-z]{3,}", source.get("title", "Unknown"))[:3]
            surname = "".join(w.capitalize() for w in words) or "Unknown"

        surname = re.sub(r"[^A-Za-z0-9]", "", surname)   # strip non-alphanum
        base    = f"[{surname}{year}]"

        if base not in self._records:
            return base
        for suffix in "abcdefghijklmnopqrstuvwxyz":
            candidate = f"[{surname}{year}{suffix}]"
            if candidate not in self._records:
                return candidate
        return f"[{surname}{year}_x]"   # overflow (extremely unlikely)

    # ------------------------------------------------------------------
    # Bibliography formatters (Markdown output)
    # ------------------------------------------------------------------

    @staticmethod
    def _md_url(url: str) -> str:
        """Render a URL as a Markdown link, or plain text if empty."""
        return f"[{url}]({url})" if url else "*URL unavailable*"

    @staticmethod
    def _apa(r: CitationRecord) -> str:
        authors = ", ".join(r.authors[:6]) + (" et al." if len(r.authors) > 6 else "")
        year    = f"({r.year})." if r.year else "(n.d.)."
        url     = f"\n{CitationRegistry._md_url(r.url)}" if r.url else ""
        return f"{authors or 'Unknown'} {year} {r.title}.{url}"

    @staticmethod
    def _ieee(idx: int, r: CitationRecord) -> str:
        authors = ", ".join(r.authors[:3]) + (" et al." if len(r.authors) > 3 else "")
        url     = f"\n{CitationRegistry._md_url(r.url)}" if r.url else ""
        return (f'[{idx}] {authors or "Unknown"}, "{r.title}," '
                f'{r.year or "n.d."}. [Online]. Available:{url}')

    @staticmethod
    def _vancouver(idx: int, r: CitationRecord) -> str:
        authors = ", ".join(r.authors[:6]) + (" et al." if len(r.authors) > 6 else "")
        url     = f"\n{CitationRegistry._md_url(r.url)}" if r.url else ""
        return f"{idx}. {authors or 'Unknown'}. {r.title}. {r.year or 'n.d.'}.{url}"

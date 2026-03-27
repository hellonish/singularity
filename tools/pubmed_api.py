"""
PubMedTool — searches PubMed via Biopython Entrez.

Requires NCBI_EMAIL env var (free, no API key needed).
credibility_base: 0.92 for peer-reviewed journals, 0.85 for preprints (bioRxiv/medRxiv).
"""
import asyncio
import os

from .base import ToolBase, ToolResult

_PREPRINT_JOURNALS = {"biorxiv", "medrxiv", "ssrn"}


def _search(query: str, max_results: int) -> list[dict]:
    from Bio import Entrez

    email = os.getenv("NCBI_EMAIL")
    if not email:
        raise EnvironmentError("NCBI_EMAIL env var is required for PubMed access")
    Entrez.email = email

    # Step 1: get PMIDs
    handle  = Entrez.esearch(db="pubmed", term=query, retmax=max_results)
    record  = Entrez.read(handle)
    handle.close()
    pmids = record.get("IdList", [])
    if not pmids:
        return []

    # Step 2: fetch full records
    handle  = Entrez.efetch(db="pubmed", id=",".join(pmids), rettype="xml", retmode="xml")
    records = Entrez.read(handle)
    handle.close()

    results = []
    for article in records.get("PubmedArticle", []):
        citation  = article.get("MedlineCitation", {})
        art       = citation.get("Article", {})
        journal   = art.get("Journal", {}).get("Title", "")
        pub_date  = _extract_date(citation)
        abstract  = " ".join(art.get("Abstract", {}).get("AbstractText", []))
        authors   = [
            f"{a.get('LastName', '')} {a.get('Initials', '')}".strip()
            for a in art.get("AuthorList", [])
            if isinstance(a, dict)
        ]
        pmid      = str(citation.get("PMID", ""))
        mesh      = [str(m["DescriptorName"]) for m in citation.get("MeshHeadingList", [])]

        is_preprint = any(p in journal.lower() for p in _PREPRINT_JOURNALS)
        results.append({
            "pmid":    pmid,
            "title":   str(art.get("ArticleTitle", "")),
            "authors": authors,
            "journal": journal,
            "date":    pub_date,
            "abstract": abstract[:500],
            "url":     f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "mesh":    mesh,
            "is_preprint": is_preprint,
        })
    return results


def _extract_date(citation: dict) -> str | None:
    try:
        pub = citation["Article"]["Journal"]["JournalIssue"]["PubDate"]
        year  = pub.get("Year",  "")
        month = pub.get("Month", "")
        day   = pub.get("Day",   "")
        return "-".join(filter(None, [year, month, day])) or None
    except (KeyError, TypeError):
        return None


class PubMedTool(ToolBase):
    name = "pubmed"

    async def call(self, query: str, max_results: int = 10, **kwargs) -> ToolResult:
        raw = await asyncio.to_thread(_search, query, max_results)

        if not raw:
            raise ValueError("No PubMed results found")

        sources = [
            {
                "title":            r["title"],
                "url":              r["url"],
                "snippet":          r["abstract"],
                "date":             r["date"],
                "authors":          r["authors"],
                "source_type":      "academic",
                "credibility_base": 0.85 if r["is_preprint"] else 0.92,
                "metadata": {
                    "pmid":    r["pmid"],
                    "journal": r["journal"],
                    "mesh":    r["mesh"],
                },
            }
            for r in raw
        ]
        avg_cred = sum(s["credibility_base"] for s in sources) / len(sources)
        content  = "\n\n".join(
            f"[{s['title']}] {s['metadata']['journal']}\n{s['snippet']}"
            for s in sources[:5]
        )
        return ToolResult(content=content, sources=sources, credibility_base=avg_cred, raw=raw)

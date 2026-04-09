"""
PdfReaderTool — extracts text and tables from PDF files or URLs.

Primary:  pdfplumber  (text + tables)
Fallback: PyMuPDF/fitz (handles scanned or malformed PDFs)

Chunks output into ~2000-token segments with page numbers.
credibility_base is 1.0 — caller should set it from the source document's credibility.
"""
import asyncio
import io
import logging
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import aiohttp

from .base import ToolBase, ToolResult, ssl_ctx

logger = logging.getLogger(__name__)

_CHUNK_CHARS = 8000   # ~2000 tokens at 4 chars/token
_TABLE_SEP   = " | "


@dataclass
class PdfPage:
    page_num: int
    text: str
    tables: list[list[list[str]]]


def _extract_with_pdfplumber(data: bytes) -> list[PdfPage]:
    import pdfplumber
    pages = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text   = page.extract_text() or ""
            tables = page.extract_tables() or []
            pages.append(PdfPage(page_num=i, text=text, tables=tables))
    return pages


def _extract_with_pymupdf(data: bytes) -> list[PdfPage]:
    import fitz
    doc   = fitz.open(stream=data, filetype="pdf")
    pages = []
    for i, page in enumerate(doc, start=1):
        text = page.get_text("text") or ""
        pages.append(PdfPage(page_num=i, text=text, tables=[]))
    return pages


def _pdf_title_from_url(url: str | None) -> str:
    """
    Derives a human-readable document title from a PDF URL.

    Extracts the filename stem (e.g. 'attention-is-all-you-need' from the path),
    converts hyphens/underscores to spaces, title-cases the result, and appends
    the domain for context.  Falls back to the domain alone when no filename
    is present.  Never returns the generic 'PDF chunk (pages X-Y)' placeholder.
    """
    if not url or url == "local":
        return "Local PDF"
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lstrip("www.")
        # Take the last non-empty path segment and strip the .pdf extension
        segments = [s for s in parsed.path.split("/") if s]
        if segments:
            stem = segments[-1]
            stem = re.sub(r"\.pdf$", "", stem, flags=re.IGNORECASE)
            # Convert hyphens/underscores/dots to spaces, then capitalize
            # only the first word — avoids over-casing acronyms like "iphone",
            # "openai", "gpt", etc. that .title() would mangle.
            stem = re.sub(r"[-_.]+", " ", stem).strip()
            if stem:
                return f"{stem.capitalize()} — {domain}"
        return domain
    except Exception:
        return "PDF Document"


def _chunk_pages(pages: list[PdfPage]) -> list[dict]:
    """Split pages into ~2000-token chunks, preserving page numbers."""
    chunks = []
    current_text  = ""
    current_start = 1

    for page in pages:
        page_text = page.text
        # Append table data as plain text
        for table in page.tables:
            rows = [_TABLE_SEP.join(str(c or "") for c in row) for row in table]
            page_text += "\n" + "\n".join(rows)

        if len(current_text) + len(page_text) > _CHUNK_CHARS and current_text:
            chunks.append({"pages": f"{current_start}-{page.page_num - 1}", "text": current_text.strip()})
            current_text  = page_text
            current_start = page.page_num
        else:
            current_text += "\n" + page_text

    if current_text.strip():
        chunks.append({"pages": f"{current_start}-{pages[-1].page_num}", "text": current_text.strip()})

    return chunks


class PdfReaderTool(ToolBase):
    name = "pdf_reader"

    async def call(self, query: str, url: str | None = None, data: bytes | None = None, **kwargs) -> ToolResult:
        """
        Args:
            query: Description or search context (used in source metadata).
            url:   URL of a PDF to download. Either url or data must be provided.
            data:  Raw PDF bytes. Overrides url if both supplied.
        """
        if data is None:
            if not url:
                raise ValueError("PdfReaderTool requires either `url` or `data`")
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_ctx()), timeout=timeout) as session:
                async with session.get(url) as resp:
                    resp.raise_for_status()
                    data = await resp.read()

        # Try pdfplumber; fall back to PyMuPDF on any error.
        # Log the primary failure so it's visible in production without
        # hiding behind the fallback's success.
        try:
            pages = await asyncio.to_thread(_extract_with_pdfplumber, data)
        except Exception as primary_exc:
            logger.warning(
                "pdfplumber extraction failed (%s), retrying with PyMuPDF: %s",
                type(primary_exc).__name__,
                primary_exc,
            )
            pages = await asyncio.to_thread(_extract_with_pymupdf, data)

        if not pages:
            raise ValueError("PDF extraction returned no pages")

        chunks = _chunk_pages(pages)
        full_text = " ".join(c["text"] for c in chunks)
        doc_title = _pdf_title_from_url(url)

        sources = [
            {
                "title":            f"{doc_title} (pp. {c['pages']})",
                "url":              url or "local",
                "content":          c["text"],          # full chunk — ingested by run_fanout
                "snippet":          c["text"][:400],    # preview only
                "date":             None,
                "source_type":      "pdf",
                "credibility_base": 1.0,  # set by caller from document source
                "metadata": {
                    "pages":       c["pages"],
                    "page_count":  len(pages),
                    "chunk_index": i,
                },
            }
            for i, c in enumerate(chunks)
        ]
        return ToolResult(
            content=full_text[:1000],
            sources=sources,
            credibility_base=1.0,
            raw={"page_count": len(pages), "chunk_count": len(chunks)},
        )

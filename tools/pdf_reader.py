"""
PdfReaderTool — extracts text and tables from PDF files or URLs.

Primary:  pdfplumber  (text + tables)
Fallback: PyMuPDF/fitz (handles scanned or malformed PDFs)

Chunks output into ~2000-token segments with page numbers.
credibility_base is 1.0 — caller should set it from the source document's credibility.
"""
import asyncio
import io
from dataclasses import dataclass
from typing import Any

import aiohttp

from .base import ToolBase, ToolResult, ssl_ctx

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
            async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_ctx())) as session:
                async with session.get(url) as resp:
                    resp.raise_for_status()
                    data = await resp.read()

        # Try pdfplumber; fall back to PyMuPDF on any error
        try:
            pages = await asyncio.to_thread(_extract_with_pdfplumber, data)
        except Exception:
            pages = await asyncio.to_thread(_extract_with_pymupdf, data)

        if not pages:
            raise ValueError("PDF extraction returned no pages")

        chunks = _chunk_pages(pages)
        full_text = " ".join(c["text"] for c in chunks)

        sources = [
            {
                "title":            f"PDF chunk (pages {c['pages']})",
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

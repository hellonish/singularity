"""
Tests for PdfReaderTool — pdfplumber + PyMuPDF fallback.

What to look for in the output:
  - sources are chunks, each with page range in metadata
  - full_transcript in metadata is the full chunk text
  - page_count tells how long the PDF is
  - chunk_count tells how many 2000-token chunks were created

Uses publicly available PDFs (arXiv, US govt).
"""
import pytest
from tools.pdf_reader import PdfReaderTool
from .conftest import assert_tool_result, print_result

# Public PDFs that don't require auth
ARXIV_PDF = "https://arxiv.org/pdf/1706.03762"   # "Attention Is All You Need"
NIST_PDF  = "https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-53r5.pdf"


async def test_pdf_reader_arxiv_url():
    """Download and extract text from a well-known arXiv PDF."""
    tool   = PdfReaderTool()
    result = await tool.call_with_retry(
        query="Attention Is All You Need transformer architecture",
        url=ARXIV_PDF,
    )

    print_result("PdfReaderTool (arXiv PDF)", result)
    assert_tool_result(result)

    for src in result.sources:
        assert src["source_type"]      == "pdf"
        assert src["credibility_base"] == 1.0
        assert "pages"       in src["metadata"]
        assert "page_count"  in src["metadata"]
        assert "chunk_index" in src["metadata"]
        assert "full_text"   in src["metadata"]
        assert len(src["metadata"]["full_text"]) > 100

    print(f"\n  Page count : {result.sources[0]['metadata']['page_count']}")
    print(f"  Chunks     : {len(result.sources)}")


async def test_pdf_reader_chunking():
    """Long PDFs should produce multiple chunks."""
    tool   = PdfReaderTool()
    result = await tool.call_with_retry(
        query="NIST cybersecurity controls",
        url=NIST_PDF,
    )

    print_result("PdfReaderTool (NIST PDF — large document)", result, max_sources=2)

    if not result.ok:
        pytest.skip(f"Could not fetch NIST PDF: {result.error}")

    print(f"\n  Page count : {result.sources[0]['metadata']['page_count']}")
    print(f"  Chunks     : {len(result.sources)}")
    # Large documents should produce multiple chunks
    assert len(result.sources) > 1, "Expected multiple chunks for a large PDF"


async def test_pdf_reader_raw_bytes():
    """Should also accept raw bytes directly (no URL fetch)."""
    import aiohttp
    from tools.base import ssl_ctx

    # Download bytes separately, then pass directly
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_ctx())) as session:
        async with session.get(ARXIV_PDF) as resp:
            pdf_bytes = await resp.read()

    tool   = PdfReaderTool()
    result = await tool.call_with_retry(
        query="attention mechanism",
        data=pdf_bytes,
    )

    print_result("PdfReaderTool (raw bytes)", result)
    assert_tool_result(result)
    assert result.sources[0]["url"] == "local"


async def test_pdf_reader_requires_url_or_data():
    """Calling without url or data should raise ValueError and return failure."""
    tool   = PdfReaderTool()
    result = await tool.call_with_retry(query="test")   # no url, no data

    assert not result.ok
    assert result.error is not None
    print(f"\n  Got expected error: {result.error}")

"""
Tests for GoogleBooksTool — Google Books API.

What to look for in the output:
  - All sources have credibility 0.85
  - Metadata has publisher, page_count, categories, and ISBN
  - preview_type tells if the book is fully viewable, partially, or none
"""
from tools.google_books import GoogleBooksTool
from .conftest import assert_tool_result, print_result

QUERY = "deep learning neural networks Ian Goodfellow"


async def test_google_books_basic():
    tool   = GoogleBooksTool()
    result = await tool.call_with_retry(QUERY)

    print_result("GoogleBooksTool", result)
    assert_tool_result(result)

    for src in result.sources:
        assert src["source_type"]      == "book"
        assert src["credibility_base"] == 0.85
        assert "publisher"    in src["metadata"]
        assert "page_count"   in src["metadata"]
        assert "categories"   in src["metadata"]
        assert "preview_type" in src["metadata"]


async def test_google_books_isbn_extraction():
    """Well-known books should have an ISBN in metadata."""
    tool   = GoogleBooksTool()
    result = await tool.call_with_retry("Designing Data-Intensive Applications Martin Kleppmann")

    print_result("GoogleBooksTool (ISBN check)", result)
    assert result.ok

    sources_with_isbn = [s for s in result.sources if s["metadata"].get("isbn")]
    print(f"\n  Sources with ISBN: {len(sources_with_isbn)} / {len(result.sources)}")
    assert len(sources_with_isbn) > 0, "Expected at least one result with an ISBN"


async def test_google_books_authors_populated():
    """Authors list should be present for most books."""
    tool   = GoogleBooksTool()
    result = await tool.call_with_retry(QUERY, max_results=5)

    assert result.ok
    sourced_with_authors = [s for s in result.sources if s.get("authors")]
    assert len(sourced_with_authors) > 0

    for src in sourced_with_authors[:3]:
        print(f"\n  {src['title'][:50]}")
        print(f"  Authors : {src['authors']}")
        print(f"  Publisher: {src['metadata']['publisher']}")
        print(f"  Pages   : {src['metadata']['page_count']}")

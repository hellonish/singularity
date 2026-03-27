"""
GoogleBooksTool — searches Google Books API.

Endpoint: https://www.googleapis.com/books/v1/volumes
Free tier works without a key (rate-limited). Set GOOGLE_BOOKS_API_KEY for higher limits.
credibility_base: 0.85 for published books.
"""
import os

import aiohttp

from .base import ToolBase, ToolResult, ssl_ctx

_BASE_URL = "https://www.googleapis.com/books/v1/volumes"


class GoogleBooksTool(ToolBase):
    name = "google_books"

    async def call(self, query: str, max_results: int = 10, **kwargs) -> ToolResult:
        params: dict = {"q": query, "maxResults": max_results, "printType": "books"}
        api_key = os.getenv("GOOGLE_BOOKS_API_KEY")
        if api_key:
            params["key"] = api_key

        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_ctx())) as session:
            async with session.get(_BASE_URL, params=params) as resp:
                resp.raise_for_status()
                data = await resp.json()

        items = data.get("items", [])
        if not items:
            raise ValueError("No Google Books results found")

        sources = []
        for item in items:
            info       = item.get("volumeInfo", {})
            access     = item.get("accessInfo", {})
            sale       = item.get("saleInfo", {})
            preview    = info.get("previewLink", "")
            isbn_list  = [
                id_["identifier"]
                for id_ in info.get("industryIdentifiers", [])
                if id_.get("type") in ("ISBN_13", "ISBN_10")
            ]
            sources.append({
                "title":            info.get("title", ""),
                "url":              preview,
                "snippet":          (info.get("description") or "")[:400],
                "date":             info.get("publishedDate"),
                "authors":          info.get("authors", []),
                "source_type":      "book",
                "credibility_base": 0.85,
                "metadata": {
                    "publisher":    info.get("publisher", ""),
                    "page_count":   info.get("pageCount"),
                    "categories":   info.get("categories", []),
                    "isbn":         isbn_list[:1][0] if isbn_list else None,
                    "language":     info.get("language", ""),
                    "preview_type": access.get("viewability", ""),
                },
            })

        content = "\n\n".join(
            f"[{s['title']}] {', '.join(s['authors'][:3])} ({s['date']})\n{s['snippet']}"
            for s in sources[:5]
        )
        return ToolResult(content=content, sources=sources, credibility_base=0.85, raw=data)

"""Guarded webpage download and main-text extraction."""
from __future__ import annotations

from urllib.parse import urljoin

import aiohttp

from .base import ToolBase, ToolResult, ssl_ctx
from .url_safety import validate_public_url

_MAX_DOWNLOAD_BYTES = 5_000_000
_MAX_REDIRECTS = 5


async def _download(url: str) -> tuple[str, str, str]:
    current = url
    timeout = aiohttp.ClientTimeout(total=30, connect=10)
    # A realistic browser User-Agent (plus Accept headers) avoids the blanket
    # 403s that CDNs/WAFs return for obviously-automated clients. Many public
    # government and news sites (e.g. cdc.gov) reject a bespoke bot UA outright.
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    # Some sites (e.g. who.int) emit very large response headers such as a
    # multi-kilobyte Content-Security-Policy. aiohttp's default 8190-byte line
    # limit raises "Got more than 8190 bytes when reading" and drops an
    # otherwise-good source, so raise the header ceiling.
    session = aiohttp.ClientSession(
        timeout=timeout,
        headers=headers,
        connector=aiohttp.TCPConnector(ssl=ssl_ctx()),
        max_line_size=65_536,
        max_field_size=65_536,
    )
    async with session:
        for _ in range(_MAX_REDIRECTS + 1):
            await validate_public_url(current)
            async with session.get(current, allow_redirects=False) as response:
                if response.status in {301, 302, 303, 307, 308}:
                    location = response.headers.get("Location")
                    if not location:
                        raise ValueError("Redirect response omitted its destination")
                    current = urljoin(current, location)
                    continue
                response.raise_for_status()
                content_type = response.headers.get("Content-Type", "").lower()
                if not any(kind in content_type for kind in ("text/html", "application/xhtml+xml", "text/plain")):
                    raise ValueError(f"Unsupported webpage content type: {content_type or 'unknown'}")
                body = bytearray()
                async for chunk in response.content.iter_chunked(64 * 1024):
                    body.extend(chunk)
                    if len(body) > _MAX_DOWNLOAD_BYTES:
                        raise ValueError("Webpage exceeds the 5 MB download limit")
                return body.decode(response.charset or "utf-8", errors="replace"), str(response.url), content_type
    raise ValueError("Webpage exceeded the redirect limit")


def _extract(html: str, url: str, max_characters: int) -> tuple[str, dict]:
    from bs4 import BeautifulSoup
    import trafilatura

    soup = BeautifulSoup(html, "html.parser")
    title = (soup.title.string.strip() if soup.title and soup.title.string else "")[:500]

    def meta(*keys: tuple[str, str]) -> str | None:
        for attribute, value in keys:
            tag = soup.find("meta", attrs={attribute: value})
            if tag and tag.get("content"):
                return str(tag["content"]).strip()
        return None

    published = meta(
        ("property", "article:published_time"),
        ("name", "date"),
        ("name", "datePublished"),
        ("itemprop", "datePublished"),
    )
    author = meta(("name", "author"), ("property", "article:author"))
    description = meta(("name", "description"), ("property", "og:description"))
    canonical_tag = soup.find("link", rel="canonical")
    canonical = str(canonical_tag.get("href")) if canonical_tag and canonical_tag.get("href") else url
    text = trafilatura.extract(
        html,
        url=url,
        include_comments=False,
        include_tables=True,
        no_fallback=False,
        favor_precision=True,
    )
    if not text:
        for node in soup(["script", "style", "noscript", "svg"]):
            node.decompose()
        text = soup.get_text("\n", strip=True)
    text = text[:max_characters]
    if not text.strip():
        raise ValueError("No readable text could be extracted from the webpage")
    return text, {
        "title": title,
        "url": url,
        "canonical_url": canonical,
        "published_at": published,
        "author": author,
        "description": description,
        "character_count": len(text),
    }


class WebFetchTool(ToolBase):
    name = "web_fetch"
    description = "Download one public webpage and extract its main text and publication metadata."
    skill_ids = ("general_web_research", "source_extraction", "citation_verification")

    async def call(self, query: str, url: str, max_characters: int = 50_000, **kwargs) -> ToolResult:
        try:
            html, final_url, content_type = await _download(url)
        except aiohttp.ClientResponseError as exc:
            # A plain HTTP download was blocked by bot protection (403/429) or
            # the origin refused it (451). Sites behind Akamai/Cloudflare
            # fingerprint the TLS/JS client, which no header set defeats — fall
            # back to a real headless browser before giving up the source.
            if exc.status not in {403, 429, 451}:
                raise
            return await self._render_fallback(query, url, max_characters)
        text, metadata = _extract(html, final_url, max_characters)
        metadata["content_type"] = content_type
        source = {
            "title": metadata["title"] or final_url,
            "url": final_url,
            "snippet": text[:500],
            "date": metadata["published_at"],
            "source_type": "web_page",
            "credibility_base": 0.75,
            "metadata": metadata,
        }
        return ToolResult(content=text, sources=[source], credibility_base=0.75, raw=None)

    async def _render_fallback(self, query: str, url: str, max_characters: int) -> ToolResult:
        """Retry a blocked page through headless Chromium.

        Imported lazily: browser_render imports _extract from this module, so a
        top-level import would be circular, and Playwright is only needed on the
        rare blocked-page path.
        """
        from .browser_render import BrowserRenderTool

        return await BrowserRenderTool().call(query, url=url, max_characters=max_characters)

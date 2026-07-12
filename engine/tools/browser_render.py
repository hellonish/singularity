"""Trusted Playwright rendering for public JavaScript webpages."""
from __future__ import annotations

from .base import ToolBase, ToolResult
from .url_safety import validate_public_url
from .web_fetch import _extract


class BrowserRenderTool(ToolBase):
    name = "browser_render"
    description = "Render one public JavaScript webpage in controlled Chromium and extract visible main text."
    skill_ids = ("general_web_research", "source_extraction")

    async def call(self, query: str, url: str, wait_milliseconds: int = 1_000, max_characters: int = 50_000, **kwargs) -> ToolResult:
        from playwright.async_api import async_playwright

        await validate_public_url(url)
        validated_hosts: set[str] = set()
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(args=["--disable-dev-shm-usage", "--no-sandbox"])
            context = await browser.new_context(java_script_enabled=True, accept_downloads=False)
            page = await context.new_page()

            async def guard(route, request):
                if request.resource_type in {"image", "media", "font", "websocket"}:
                    await route.abort()
                    return
                try:
                    host = request.url.split("/", 3)[2]
                    if host not in validated_hosts:
                        await validate_public_url(request.url)
                        validated_hosts.add(host)
                except Exception:
                    await route.abort()
                    return
                await route.continue_()

            await page.route("**/*", guard)
            response = await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            if response is None:
                raise ValueError("Browser navigation returned no response")
            await page.wait_for_timeout(wait_milliseconds)
            final_url = page.url
            await validate_public_url(final_url)
            html = await page.content()
            await browser.close()
        text, metadata = _extract(html, final_url, max_characters)
        source = {
            "title": metadata["title"] or final_url,
            "url": final_url,
            "snippet": text[:500],
            "date": metadata["published_at"],
            "source_type": "browser_page",
            "credibility_base": 0.70,
            "metadata": metadata,
        }
        return ToolResult(content=text, sources=[source], credibility_base=0.70, raw=None)

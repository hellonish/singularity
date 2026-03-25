"""
TranslationTool — translates text between languages.

Primary:  MyMemory API  — free, no key required (500 chars/day anonymous;
          set MYMEMORY_EMAIL for 5 000 chars/day).
          https://api.mymemory.translated.net
Fallback: Google Translate (requires GOOGLE_TRANSLATE_API_KEY env var)

Appends [low-confidence translation] to output when confidence < 0.8.
"""
import os

import aiohttp

from .base import ToolBase, ToolResult, ssl_ctx

_MYMEMORY_URL = "https://api.mymemory.translated.net/get"


class TranslationTool(ToolBase):
    name = "translation"

    async def call(
        self,
        query: str,             # text to translate (used as the source text)
        source_lang: str = "auto",
        target_lang: str = "en",
        **kwargs,
    ) -> ToolResult:
        try:
            return await self._mymemory(query, source_lang, target_lang)
        except Exception as primary_exc:
            google_key = os.getenv("GOOGLE_TRANSLATE_API_KEY")
            if not google_key:
                raise primary_exc
            return await self._google_translate(query, source_lang, target_lang, google_key)

    async def _mymemory(self, text: str, source: str, target: str) -> ToolResult:
        langpair = f"autodetect|{target}" if source == "auto" else f"{source}|{target}"
        params: dict = {"q": text, "langpair": langpair}

        email = os.getenv("MYMEMORY_EMAIL", "")
        if email:
            params["de"] = email           # raises daily limit to 5 000 chars

        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_ctx())) as session:
            async with session.get(_MYMEMORY_URL, params=params) as resp:
                resp.raise_for_status()
                data = await resp.json()

        if data.get("responseStatus") != 200:
            raise RuntimeError(f"MyMemory error: {data.get('responseStatus')}")

        resp_data   = data["responseData"]
        translated  = resp_data.get("translatedText", "")
        confidence  = float(resp_data.get("match", 1.0))
        detected    = source if source != "auto" else target   # MyMemory doesn't return detected lang

        low_conf_tag = " [low-confidence translation]" if confidence < 0.8 else ""
        return self._build_result(text, translated + low_conf_tag, detected, target, confidence, data)

    async def _google_translate(self, text: str, source: str, target: str, api_key: str) -> ToolResult:
        url    = "https://translation.googleapis.com/language/translate/v2"
        params = {"q": text, "target": target, "key": api_key}
        if source != "auto":
            params["source"] = source

        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_ctx())) as session:
            async with session.post(url, params=params) as resp:
                resp.raise_for_status()
                data = await resp.json()

        translation = data["data"]["translations"][0]
        translated  = translation.get("translatedText", "")
        detected    = translation.get("detectedSourceLanguage", source)

        return self._build_result(text, translated, detected, target, 0.95, data)

    @staticmethod
    def _build_result(
        original: str, translated: str, source_lang: str, target_lang: str,
        confidence: float, raw: dict,
    ) -> ToolResult:
        content = translated
        sources = [{
            "title":            f"Translation: {source_lang} → {target_lang}",
            "url":              "",
            "snippet":          translated[:300],
            "date":             None,
            "source_type":      "translation",
            "credibility_base": confidence,
            "metadata": {
                "original":    original,
                "translated":  translated,
                "source_lang": source_lang,
                "target_lang": target_lang,
                "confidence":  confidence,
            },
        }]
        return ToolResult(content=content, sources=sources, credibility_base=confidence, raw=raw)

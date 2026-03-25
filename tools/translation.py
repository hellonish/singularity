"""
TranslationTool — translates text between languages.

Primary:  LibreTranslate (free, self-hostable; set LIBRETRANSLATE_URL, default: public API)
Fallback: Google Translate (requires GOOGLE_TRANSLATE_API_KEY env var)

Appends [low-confidence translation] to output when confidence < 0.8.
"""
import os

import aiohttp

from .base import ToolBase, ToolResult

_DEFAULT_LIBRE_URL = "https://libretranslate.com/translate"
_LIBRE_API_KEY_ENV = "LIBRETRANSLATE_API_KEY"   # optional for public instance


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
            return await self._libretranslate(query, source_lang, target_lang)
        except Exception as libre_exc:
            google_key = os.getenv("GOOGLE_TRANSLATE_API_KEY")
            if not google_key:
                raise libre_exc
            return await self._google_translate(query, source_lang, target_lang, google_key)

    async def _libretranslate(self, text: str, source: str, target: str) -> ToolResult:
        url     = os.getenv("LIBRETRANSLATE_URL", _DEFAULT_LIBRE_URL)
        api_key = os.getenv(_LIBRE_API_KEY_ENV, "")

        payload = {"q": text, "source": source, "target": target, "format": "text"}
        if api_key:
            payload["api_key"] = api_key

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                resp.raise_for_status()
                data = await resp.json()

        translated   = data.get("translatedText", "")
        detected     = data.get("detectedLanguage", {}).get("language", source)
        confidence   = float(data.get("detectedLanguage", {}).get("confidence", 1.0)) / 100
        low_conf_tag = " [low-confidence translation]" if confidence < 0.8 else ""

        return self._build_result(text, translated + low_conf_tag, detected, target, confidence, data)

    async def _google_translate(self, text: str, source: str, target: str, api_key: str) -> ToolResult:
        url    = "https://translation.googleapis.com/language/translate/v2"
        params = {"q": text, "target": target, "key": api_key}
        if source != "auto":
            params["source"] = source

        async with aiohttp.ClientSession() as session:
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

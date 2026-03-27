"""
Tests for TranslationTool — LibreTranslate primary, Google Translate fallback.

What to look for in the output:
  - translated text is non-empty and different from input (for non-English input)
  - source_lang is detected correctly
  - confidence < 0.8 appends [low-confidence translation] to the output
  - credibility_base equals the confidence score

Set LIBRETRANSLATE_URL if self-hosting, otherwise the public instance is used.
Set GOOGLE_TRANSLATE_API_KEY to test the fallback.
"""
import pytest
from tools.translation import TranslationTool
from .conftest import assert_tool_result, print_result

# Short texts in various languages
FRENCH_TEXT  = "La vie est belle et pleine de surprises."
SPANISH_TEXT = "El aprendizaje automático está transformando la industria."
GERMAN_TEXT  = "Datenschutz ist ein grundlegendes Menschenrecht."
JAPANESE_TEXT = "人工知能は社会を変えています。"


async def test_translation_french_to_english():
    tool   = TranslationTool()
    result = await tool.call_with_retry(
        FRENCH_TEXT, source_lang="fr", target_lang="en"
    )

    print_result("TranslationTool (FR → EN)", result)
    assert_tool_result(result)

    src = result.sources[0]
    assert src["source_type"]           == "translation"
    assert src["metadata"]["original"]  == FRENCH_TEXT
    assert src["metadata"]["source_lang"] == "fr"
    assert src["metadata"]["target_lang"] == "en"
    assert len(src["metadata"]["translated"]) > 0
    assert src["metadata"]["translated"] != FRENCH_TEXT

    print(f"\n  Original   : {FRENCH_TEXT}")
    print(f"  Translated : {src['metadata']['translated']}")
    print(f"  Confidence : {src['metadata']['confidence']:.2f}")


async def test_translation_auto_detect():
    """source_lang='auto' should detect the language automatically."""
    tool   = TranslationTool()
    result = await tool.call_with_retry(
        SPANISH_TEXT, source_lang="auto", target_lang="en"
    )

    print_result("TranslationTool (auto → EN)", result)
    assert result.ok

    src = result.sources[0]
    print(f"\n  Original   : {SPANISH_TEXT}")
    print(f"  Translated : {src['metadata']['translated']}")
    print(f"  Detected   : {src['metadata']['source_lang']}")


async def test_translation_confidence_in_credibility():
    """credibility_base should equal the confidence score."""
    tool   = TranslationTool()
    result = await tool.call_with_retry(GERMAN_TEXT, source_lang="de", target_lang="en")

    assert result.ok
    src = result.sources[0]
    assert abs(result.credibility_base - src["metadata"]["confidence"]) < 0.001, (
        f"credibility_base {result.credibility_base} should equal confidence {src['metadata']['confidence']}"
    )


async def test_translation_low_confidence_tag():
    """When confidence < 0.8, the output should be tagged."""
    # We can't force low confidence from a test, so we just verify the logic
    # by checking that high-confidence translations do NOT have the tag
    tool   = TranslationTool()
    result = await tool.call_with_retry(FRENCH_TEXT, source_lang="fr", target_lang="en")

    assert result.ok
    translated = result.sources[0]["metadata"]["translated"]
    confidence = result.sources[0]["metadata"]["confidence"]

    has_tag = "[low-confidence translation]" in translated
    if confidence >= 0.8:
        assert not has_tag, f"High-confidence translation should not have low-conf tag"
    else:
        assert has_tag, f"Low-confidence ({confidence:.2f}) translation should have tag"

    print(f"\n  Confidence  : {confidence:.2f}")
    print(f"  Has low-conf tag: {has_tag}")


async def test_translation_multiple_languages():
    """Translate a few different languages and show results side-by-side."""
    tool  = TranslationTool()
    texts = [
        (FRENCH_TEXT,   "fr", "French"),
        (SPANISH_TEXT,  "es", "Spanish"),
        (GERMAN_TEXT,   "de", "German"),
    ]
    print(f"\n{'─'*60}")
    for text, lang, label in texts:
        result = await tool.call_with_retry(text, source_lang=lang, target_lang="en")
        if result.ok:
            translated = result.sources[0]["metadata"]["translated"]
            print(f"  {label:<10}: {translated[:80]}")
        else:
            print(f"  {label:<10}: ERROR — {result.error}")
    print(f"{'─'*60}")

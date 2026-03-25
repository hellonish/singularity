"""
Tests for YouTubeTranscriptTool — DuckDuckGo → video IDs → transcripts.

What to look for in the output:
  - Academic/conference channels get credibility 0.80; general 0.65
  - full_transcript in metadata is the complete transcript text
  - duration_secs gives an estimate of video length
"""
from tools.youtube_transcript import YouTubeTranscriptTool
from .conftest import assert_tool_result, print_result

QUERY = "how transformers work attention mechanism explained"


async def test_youtube_transcript_basic():
    tool   = YouTubeTranscriptTool()
    result = await tool.call_with_retry(QUERY, max_results=3)

    print_result("YouTubeTranscriptTool", result)
    assert_tool_result(result)

    for src in result.sources:
        assert src["source_type"] == "video"
        assert src["credibility_base"] in (0.65, 0.80)
        assert "video_id"        in src["metadata"]
        assert "duration_secs"   in src["metadata"]
        assert "full_transcript" in src["metadata"]
        assert len(src["metadata"]["full_transcript"]) > 100


async def test_youtube_transcript_academic_channel_boost():
    """Known academic/conference channels should get 0.80 credibility."""
    tool   = YouTubeTranscriptTool()
    result = await tool.call_with_retry("NeurIPS 2023 keynote large language models", max_results=3)

    print_result("YouTubeTranscriptTool (academic query)", result)
    assert result.ok

    # Print credibility for each video found
    for src in result.sources:
        print(f"\n  [{src['credibility_base']:.2f}] {src['url']}")


async def test_youtube_transcript_full_text_length():
    """Full transcript should be substantially longer than the snippet."""
    tool   = YouTubeTranscriptTool()
    result = await tool.call_with_retry(QUERY, max_results=2)

    assert result.ok
    for src in result.sources:
        snippet_len    = len(src.get("snippet", ""))
        full_text_len  = len(src["metadata"]["full_transcript"])
        assert full_text_len >= snippet_len, (
            f"full_transcript ({full_text_len}) should be >= snippet ({snippet_len})"
        )
        print(f"\n  snippet: {snippet_len} chars | full_transcript: {full_text_len} chars")

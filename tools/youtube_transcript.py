"""
YouTubeTranscriptTool — finds relevant YouTube videos and returns their transcripts.

Step 1: DuckDuckGo search with `site:youtube.com` to find video IDs.
Step 2: youtube-transcript-api to fetch transcripts.

credibility_base: 0.80 for known conference/academic channels, 0.65 otherwise.
"""
import asyncio
import re

from .base import ToolBase, ToolResult

# Channel handles/keywords associated with higher credibility
_ACADEMIC_CHANNELS = {
    "ted", "tedx", "google", "stanford", "mit", "harvard", "ycombinator",
    "neurips", "icml", "iclr", "pycon", "djangocon", "kurzgesagt",
}

_VIDEO_ID_RE = re.compile(r"(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})")


def _extract_video_id(url: str) -> str | None:
    m = _VIDEO_ID_RE.search(url)
    return m.group(1) if m else None


def _ddg_youtube_search(query: str, max_results: int) -> list[str]:
    from duckduckgo_search import DDGS
    results = DDGS().text(f"site:youtube.com {query}", max_results=max_results * 2)
    video_ids = []
    for r in results:
        vid = _extract_video_id(r.get("href", "") or r.get("url", ""))
        if vid and vid not in video_ids:
            video_ids.append(vid)
        if len(video_ids) >= max_results:
            break
    return video_ids


def _fetch_transcript(video_id: str) -> dict | None:
    from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
    try:
        entries   = YouTubeTranscriptApi.get_transcript(video_id)
        full_text = " ".join(e["text"] for e in entries)
        return {
            "video_id": video_id,
            "url":      f"https://www.youtube.com/watch?v={video_id}",
            "text":     full_text,
            "duration": entries[-1]["start"] if entries else 0,
        }
    except (TranscriptsDisabled, NoTranscriptFound):
        return None


def _is_academic(url: str) -> bool:
    url_lower = url.lower()
    return any(kw in url_lower for kw in _ACADEMIC_CHANNELS)


class YouTubeTranscriptTool(ToolBase):
    name = "youtube_transcript"

    async def call(self, query: str, max_results: int = 5, **kwargs) -> ToolResult:
        video_ids = await asyncio.to_thread(_ddg_youtube_search, query, max_results)

        if not video_ids:
            raise ValueError("No YouTube videos found for query")

        transcripts = await asyncio.gather(
            *[asyncio.to_thread(_fetch_transcript, vid) for vid in video_ids]
        )

        sources = []
        for transcript in transcripts:
            if transcript is None:
                continue
            cred = 0.80 if _is_academic(transcript["url"]) else 0.65
            sources.append({
                "title":            f"YouTube: {transcript['video_id']}",
                "url":              transcript["url"],
                "snippet":          transcript["text"][:400],
                "date":             None,
                "source_type":      "video",
                "credibility_base": cred,
                "metadata": {
                    "video_id":       transcript["video_id"],
                    "duration_secs":  transcript["duration"],
                    "full_transcript": transcript["text"],
                },
            })

        if not sources:
            raise ValueError("Could not retrieve transcripts for any found videos")

        avg_cred = sum(s["credibility_base"] for s in sources) / len(sources)
        content  = "\n\n".join(
            f"[YouTube: {s['metadata']['video_id']}]\n{s['snippet']}" for s in sources[:3]
        )
        return ToolResult(content=content, sources=sources, credibility_base=avg_cred, raw=transcripts)

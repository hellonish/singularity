"""
YouTubeTranscriptTool — finds relevant YouTube videos and returns their transcripts.

Step 1: DuckDuckGo search with `site:youtube.com` to find video IDs.
Step 2: youtube-transcript-api (v1.x) to fetch transcripts.

Transcript fetch strategy:
  - Tries all available transcript languages, preferring English.
  - Retries once on 429 (YouTube rate-limit) with a 5-second back-off.
  - Tries up to `max_results * 3` candidate videos so at least `max_results`
    succeed even when some videos have transcripts disabled.

credibility_base: 0.80 for known conference/academic channels, 0.65 otherwise.
"""
import asyncio
import re
import time

from .base import ToolBase, ToolResult

_ACADEMIC_CHANNELS = {
    "ted", "tedx", "google", "stanford", "mit", "harvard", "ycombinator",
    "neurips", "icml", "iclr", "pycon", "djangocon", "kurzgesagt",
}

_VIDEO_ID_RE = re.compile(r"(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})")


def _extract_video_id(url: str) -> str | None:
    m = _VIDEO_ID_RE.search(url)
    return m.group(1) if m else None


def _ddg_youtube_search(query: str, max_results: int) -> list[str]:
    from ddgs import DDGS
    results = DDGS().text(f"site:youtube.com {query}", max_results=max_results * 3)
    video_ids: list[str] = []
    for r in results:
        vid = _extract_video_id(r.get("href", "") or r.get("url", ""))
        if vid and vid not in video_ids:
            video_ids.append(vid)
    return video_ids


def _fetch_transcript(video_id: str) -> dict | None:
    """
    Attempts to fetch a transcript for `video_id`.

    Tries all available languages returned by list_transcripts(), preferring
    manually created English transcripts first, then auto-generated, then any
    other language.  Retries once on HTTP 429 with a 5-second sleep.

    Returns a dict with video_id, url, text, duration on success; None otherwise.
    """
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import (
        TranscriptsDisabled,
        NoTranscriptFound,
        YouTubeRequestFailed,
    )

    api = YouTubeTranscriptApi()

    for attempt in range(2):
        try:
            transcript_list = api.list(video_id)

            # Build priority order: manual EN → auto EN → any manual → any auto
            candidates = []
            for t in transcript_list:
                priority = (
                    0 if (not t.is_generated and t.language_code.startswith("en")) else
                    1 if (t.is_generated and t.language_code.startswith("en")) else
                    2 if not t.is_generated else
                    3
                )
                candidates.append((priority, t))

            if not candidates:
                return None

            candidates.sort(key=lambda x: x[0])
            transcript = candidates[0][1].fetch()

            entries   = list(transcript)
            full_text = " ".join(e.text for e in entries)
            duration  = entries[-1].start if entries else 0
            return {
                "video_id": video_id,
                "url":      f"https://www.youtube.com/watch?v={video_id}",
                "text":     full_text,
                "duration": duration,
            }

        except YouTubeRequestFailed as exc:
            if "429" in str(exc) and attempt == 0:
                time.sleep(5)
                continue
            return None
        except (TranscriptsDisabled, NoTranscriptFound):
            return None
        except Exception:
            return None

    return None


def _is_academic(url: str) -> bool:
    url_lower = url.lower()
    return any(kw in url_lower for kw in _ACADEMIC_CHANNELS)


class YouTubeTranscriptTool(ToolBase):
    name = "youtube_transcript"

    async def call(self, query: str, max_results: int = 5, **kwargs) -> ToolResult:
        """
        Searches DuckDuckGo for YouTube videos matching `query`, then fetches
        transcripts for up to `max_results * 3` candidates until `max_results`
        succeed.

        Args:
            query:       Search query forwarded to DuckDuckGo.
            max_results: Target number of successful transcripts.

        Returns:
            ToolResult with one source per successful transcript.
        """
        video_ids = await asyncio.to_thread(_ddg_youtube_search, query, max_results)

        if not video_ids:
            raise ValueError("No YouTube videos found for query")

        # Fetch all candidates concurrently; accept first max_results that succeed
        transcripts_raw = await asyncio.gather(
            *[asyncio.to_thread(_fetch_transcript, vid) for vid in video_ids]
        )

        sources = []
        for transcript in transcripts_raw:
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
                    "video_id":        transcript["video_id"],
                    "duration_secs":   transcript["duration"],
                    "full_transcript": transcript["text"],
                },
            })
            if len(sources) >= max_results:
                break

        if not sources:
            raise ValueError(
                f"Could not retrieve transcripts from any of the {len(video_ids)} "
                "candidate videos (transcripts disabled or rate-limited)"
            )

        avg_cred = sum(s["credibility_base"] for s in sources) / len(sources)
        content  = "\n\n".join(
            f"[YouTube: {s['metadata']['video_id']}]\n{s['snippet']}" for s in sources[:3]
        )
        return ToolResult(content=content, sources=sources, credibility_base=avg_cred, raw=transcripts_raw)

from tools.youtube_transcript import YouTubeTranscriptTool
from ..base import BaseRetrievalSkill


class VideoSearchSkill(BaseRetrievalSkill):
    name   = "video_search"
    min_ok = 1

    async def _fetch(self, node, query=None):
        return await YouTubeTranscriptTool().call_with_retry(
            query or node.description, max_results=self._depth_n(node, default=5)
        )

from tools.web_fetch import WebFetchTool
from ..base import BaseRetrievalSkill


class MultimediaSearchSkill(BaseRetrievalSkill):
    name   = "multimedia_search"
    min_ok = 1

    async def _fetch(self, node, query=None):
        return await WebFetchTool().call_with_retry(
            f"{query or node.description} video podcast audio presentation slides",
            max_results=self._depth_n(node),
        )

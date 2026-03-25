from tools.web_fetch import WebFetchTool
from .._base import BaseRetrievalSkill


class WebSearchSkill(BaseRetrievalSkill):
    name   = "web_search"
    min_ok = 3

    async def _fetch(self, node):
        return await WebFetchTool().call_with_retry(
            node.description, max_results=self._depth_n(node)
        )

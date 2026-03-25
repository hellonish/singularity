from tools.web_fetch import WebFetchTool
from .._base import BaseRetrievalSkill


class GovSearchSkill(BaseRetrievalSkill):
    name   = "gov_search"
    min_ok = 2

    async def _fetch(self, node):
        return await WebFetchTool().call_with_retry(
            f"site:.gov {node.description}",
            max_results=self._depth_n(node),
        )

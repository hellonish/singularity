from tools.standards_fetch import StandardsFetchTool
from ..base import BaseRetrievalSkill


class StandardsSearchSkill(BaseRetrievalSkill):
    name   = "standards_search"
    min_ok = 1

    async def _fetch(self, node, query=None):
        return await StandardsFetchTool().call_with_retry(
            query or node.description, max_results=self._depth_n(node)
        )

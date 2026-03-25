from tools.web_fetch import WebFetchTool
from .._base import BaseRetrievalSkill


class PatentSearchSkill(BaseRetrievalSkill):
    name   = "patent_search"
    min_ok = 1

    async def _fetch(self, node):
        return await WebFetchTool().call_with_retry(
            f"patent {node.description} patents.google.com OR patents.justia.com",
            max_results=self._depth_n(node),
        )

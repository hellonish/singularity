from tools.github_api import GitHubTool
from ..base import BaseRetrievalSkill


class CodeSearchSkill(BaseRetrievalSkill):
    name   = "code_search"
    min_ok = 2

    async def _fetch(self, node, query=None):
        return await GitHubTool().call_with_retry(
            self._to_query(query or node.description), max_results=self._depth_n(node)
        )

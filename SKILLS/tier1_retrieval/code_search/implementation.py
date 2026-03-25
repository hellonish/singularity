from tools.github_api import GitHubTool
from .._base import BaseRetrievalSkill


class CodeSearchSkill(BaseRetrievalSkill):
    name   = "code_search"
    min_ok = 2

    async def _fetch(self, node):
        return await GitHubTool().call_with_retry(
            node.description, max_results=self._depth_n(node)
        )

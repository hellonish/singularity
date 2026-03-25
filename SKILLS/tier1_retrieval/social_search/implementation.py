from tools.web_fetch import WebFetchTool
from .._base import BaseRetrievalSkill


class SocialSearchSkill(BaseRetrievalSkill):
    name   = "social_search"
    min_ok = 2

    async def _fetch(self, node):
        return await WebFetchTool().call_with_retry(
            f"{node.description} reddit.com OR linkedin.com OR medium.com",
            max_results=self._depth_n(node),
        )

from tools.web_fetch import WebFetchTool
from ..base import BaseRetrievalSkill

_FORUMS = "stackoverflow.com OR reddit.com OR news.ycombinator.com OR dev.to"


class ForumSearchSkill(BaseRetrievalSkill):
    name   = "forum_search"
    min_ok = 2

    async def _fetch(self, node, query=None):
        return await WebFetchTool().call_with_retry(
            f"{query or node.description} ({_FORUMS})",
            max_results=self._depth_n(node),
        )

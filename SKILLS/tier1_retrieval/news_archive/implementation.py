from tools.web_fetch import WebFetchTool
from .._base import BaseRetrievalSkill

_NEWS = "reuters.com OR apnews.com OR bbc.com OR nytimes.com OR wsj.com OR ft.com"


class NewsArchiveSkill(BaseRetrievalSkill):
    name   = "news_archive"
    min_ok = 2

    async def _fetch(self, node):
        return await WebFetchTool().call_with_retry(
            f"{node.description} ({_NEWS})",
            max_results=self._depth_n(node),
        )

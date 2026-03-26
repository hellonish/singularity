from tools.google_books import GoogleBooksTool
from ..base import BaseRetrievalSkill


class BookSearchSkill(BaseRetrievalSkill):
    name   = "book_search"
    min_ok = 2

    async def _fetch(self, node, query=None):
        return await GoogleBooksTool().call_with_retry(
            query or node.description, max_results=self._depth_n(node)
        )

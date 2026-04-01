from tools.dataset_hub import DatasetHubTool
from ..base import BaseRetrievalSkill


class DatasetSearchSkill(BaseRetrievalSkill):
    name   = "dataset_search"
    min_ok = 2

    async def _fetch(self, node, query=None):
        return await DatasetHubTool().call_with_retry(
            self._to_query(query or node.description), max_results=self._depth_n(node)
        )

from tools.courtlistener import CourtListenerTool
from ..base import BaseRetrievalSkill


class LegalSearchSkill(BaseRetrievalSkill):
    """
    HARD RULE (from ROBUSTNESS.md): if jurisdiction filter is in acceptance
    and zero results survive, return FAILED — do NOT fall back to web search
    for legal conclusions.
    """
    name   = "legal_search"
    min_ok = 1   # even a single primary case/statute is OK

    async def _fetch(self, node, query=None):
        return await CourtListenerTool().call_with_retry(
            query or node.description, max_results=self._depth_n(node)
        )

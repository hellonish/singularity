"""
clinical_search — queries PubMed and ClinicalTrials.gov in parallel.
"""
import asyncio

from tools.pubmed_api import PubMedTool
from tools.clinicaltrials import ClinicalTrialsTool
from ..base import BaseRetrievalSkill


class ClinicalSearchSkill(BaseRetrievalSkill):
    name   = "clinical_search"
    min_ok = 2

    async def run(self, node, ctx, client, registry):
        half = max(self._depth_n(node) // 2, 3)

        pubmed_res, trials_res = await asyncio.gather(
            PubMedTool().call_with_retry(node.description, max_results=half),
            ClinicalTrialsTool().call_with_retry(node.description, max_results=half),
            return_exceptions=True,
        )

        sources: list[dict] = []
        for res in (pubmed_res, trials_res):
            if not isinstance(res, Exception) and res.ok:
                sources.extend(res.sources)

        if not sources:
            return self._fail(node, "No clinical sources found (PubMed + ClinicalTrials.gov)")

        self._register_all(sources, node, ctx)

        return self._build_output(
            sources, node,
            coverage_notes=f"{len(sources)} clinical source(s) from PubMed + ClinicalTrials.gov",
        )

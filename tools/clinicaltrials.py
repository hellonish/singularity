"""
ClinicalTrialsTool — searches ClinicalTrials.gov via the v2 REST API.

Endpoint: https://clinicaltrials.gov/api/v2/studies
Free, no authentication required.
credibility_base: 1.0 (official government registry).
"""
import aiohttp

from .base import ToolBase, ToolResult

_BASE_URL = "https://clinicaltrials.gov/api/v2/studies"


class ClinicalTrialsTool(ToolBase):
    name = "clinicaltrials"

    async def call(self, query: str, max_results: int = 10, **kwargs) -> ToolResult:
        params = {
            "query.term": query,
            "pageSize":   max_results,
            "fields":     "NCTId,BriefTitle,OverallStatus,Phase,Condition,"
                          "InterventionName,PrimaryCompletionDate,ResultsFirstPostDate,"
                          "BriefSummary",
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(_BASE_URL, params=params) as resp:
                resp.raise_for_status()
                data = await resp.json()

        studies = data.get("studies", [])
        if not studies:
            raise ValueError("No ClinicalTrials results found")

        sources = []
        for study in studies:
            proto  = study.get("protocolSection", {})
            id_mod = proto.get("identificationModule", {})
            status = proto.get("statusModule", {})
            design = proto.get("designModule", {})
            cond   = proto.get("conditionsModule", {})
            interv = proto.get("armsInterventionsModule", {})
            desc   = proto.get("descriptionModule", {})

            nct_id = id_mod.get("nctId", "")
            phases = design.get("phases", [])
            sources.append({
                "title":            id_mod.get("briefTitle", ""),
                "url":              f"https://clinicaltrials.gov/study/{nct_id}",
                "snippet":          (desc.get("briefSummary") or "")[:400],
                "date":             status.get("primaryCompletionDateStruct", {}).get("date"),
                "source_type":      "clinical",
                "credibility_base": 1.0,
                "metadata": {
                    "nct_id":        nct_id,
                    "status":        status.get("overallStatus", ""),
                    "phase":         phases[0] if phases else "N/A",
                    "conditions":    cond.get("conditions", []),
                    "interventions": [
                        i.get("interventionName", "")
                        for i in interv.get("interventions", [])
                    ],
                    "has_results":   bool(status.get("resultsFirstPostDateStruct")),
                },
            })

        content = "\n\n".join(
            f"[{s['title']}] {s['metadata']['status']} — {s['metadata']['phase']}\n{s['snippet']}"
            for s in sources[:5]
        )
        return ToolResult(content=content, sources=sources, credibility_base=1.0, raw=data)

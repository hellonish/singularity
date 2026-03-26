"""
Retriever agent — Phase A of the research pipeline.
Selects retrieval skills, fans out queries, ingests results into the vector store.
"""
from __future__ import annotations

import asyncio
import json
import re

from models import ExecutionContext, PlanNode
from skills import SKILL_REGISTRY, TIER1_SKILLS


class Retriever:
    """
    Encapsulates Phase A: skill selection → parallel fanout → Qdrant ingest.

    Usage:
        retriever = Retriever(llm_client, vector_store_client)
        active_skills = await retriever.run(query, strength, run_id, collection_name, ctx)
    """

    def __init__(self, client, vs):
        self.client = client
        self.vs = vs

    async def run(
        self,
        query: str,
        strength,           # StrengthConfig
        run_id: str,
        collection_name: str,
        ctx: ExecutionContext,
    ) -> list[str]:
        """Run retrieval phase. Returns list of active skill names."""
        from agents.orchestrator.config import PLANNER_MODEL

        retrieval_registry = {k: v for k, v in SKILL_REGISTRY.items() if k in TIER1_SKILLS}

        skill_plan_raw = self.client.generate_text(
            prompt=(
                f"mode: retrieval_plan\n"
                f"query: {query}\n"
                f"available_skills: {', '.join(retrieval_registry.keys())}\n"
                f"select_n_skills: {strength.retrieval_skill_count}\n"
                f"queries_per_skill: {strength.queries_per_skill}\n\n"
                f"Return JSON: {{\"skill_queries\": {{\"skill_name\": [\"query1\", ...]}}}}\n"
                f"Select the {strength.retrieval_skill_count} most relevant skills for this query.\n"
                f"Generate exactly {strength.queries_per_skill} diverse sub-queries per skill."
            ),
            system_prompt=(
                "You are a retrieval planner. Return ONLY valid JSON with no prose. "
                "The JSON must have a single key 'skill_queries' mapping skill names to "
                "lists of query strings."
            ),
            temperature=0.3,
        )

        skill_queries = self._parse_skill_queries(skill_plan_raw, strength, query, retrieval_registry)
        active_skills = list(skill_queries.keys())
        print(f"  Active skills: {active_skills}")

        async def _run_skill(skill_name: str, queries: list[str]) -> None:
            skill = retrieval_registry.get(skill_name)
            if skill is None:
                print(f"  [WARN] skill '{skill_name}' not in retrieval registry — skipping")
                return
            node = PlanNode(
                node_id=f"retrieval_{skill_name}",
                description=query,
                skill=skill_name,
                depends_on=[],
                acceptance=[],
                parallelizable=True,
                output_slot=f"retrieval_{skill_name}",
            )
            summary = await skill.run_fanout(
                queries=queries,
                run_id=run_id,
                collection_name=collection_name,
                node=node,
                ctx=ctx,
                vs=self.vs,
            )
            print(f"  [{skill_name}] {summary['sources_found']} sources → {summary['chunks_stored']} chunks")

        await asyncio.gather(*[_run_skill(name, queries) for name, queries in skill_queries.items()])
        self.vs.register_run_in_cache(run_id, query)
        return active_skills

    @staticmethod
    def _parse_skill_queries(raw: str, strength, fallback_query: str, retrieval_registry: dict) -> dict[str, list[str]]:
        m = re.search(r'```(?:json)?\s*\n(.*?)\n```', raw, re.DOTALL)
        text = m.group(1) if m else raw.strip()
        start = text.find("{")
        if start != -1:
            text = text[start:]
        try:
            obj = json.loads(text)
            sq = obj.get("skill_queries", obj)
            if isinstance(sq, dict):
                result: dict[str, list[str]] = {}
                q = strength.queries_per_skill
                for skill, queries in list(sq.items())[:strength.retrieval_skill_count]:
                    if skill not in retrieval_registry:
                        continue
                    if not isinstance(queries, list) or len(queries) == 0:
                        queries = [fallback_query]
                    while len(queries) < q:
                        queries.append(fallback_query)
                    result[skill] = queries[:q]
                if result:
                    return result
        except Exception:
            pass
        fallback_skills = list(retrieval_registry.keys())[:strength.retrieval_skill_count]
        return {s: [fallback_query] * strength.queries_per_skill for s in fallback_skills}

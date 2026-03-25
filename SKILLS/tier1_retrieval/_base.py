"""
BaseRetrievalSkill — shared pattern for all 18 tier-1 retrieval skills.

Subclass this and implement _fetch(node) → ToolResult.
For multi-tool skills (academic, clinical, financial) override run() directly.
"""
from orchestrator.skills import SkillBase
from orchestrator.models import NodeStatus, PlanNode


class BaseRetrievalSkill(SkillBase):
    # Minimum sources required for NodeStatus.OK (vs PARTIAL)
    min_ok: int = 2

    # ---------------------------------------------------------------------------
    # Override in subclass
    # ---------------------------------------------------------------------------

    async def _fetch(self, node: PlanNode):
        """Call the tool and return a ToolResult. Raise on hard error."""
        raise NotImplementedError

    # ---------------------------------------------------------------------------
    # Shared run() logic
    # ---------------------------------------------------------------------------

    async def run(self, node, ctx, client, registry):
        try:
            result = await self._fetch(node)
        except Exception as exc:
            return self._fail(node, str(exc))

        if not result.ok:
            return self._fail(node, result.error)

        sources = list(result.sources)

        # Register every source in the citation registry
        cit_reg = getattr(ctx, "citation_registry", None)
        if cit_reg is not None:
            for src in sources:
                cid = cit_reg.register(src, self.name, node.output_slot)
                src["citation_id"] = cid

        n      = len(sources)
        status = (NodeStatus.OK      if n >= self.min_ok else
                  NodeStatus.PARTIAL if n > 0           else
                  NodeStatus.FAILED)
        avg_cred = (sum(s.get("credibility_base", 0.75) for s in sources) / n
                    if n else 0.0)

        return {
            "skill_name":     self.name,
            "sources":        sources,
            "query_used":     node.description,
            "result_count":   n,
            "coverage_notes": self._notes(n),
            "fallback_used":  False,
        }, status, avg_cred

    # ---------------------------------------------------------------------------
    # Helpers available to all subclasses
    # ---------------------------------------------------------------------------

    def _fail(self, node: PlanNode, error: str | None):
        return {
            "skill_name":     self.name,
            "sources":        [],
            "query_used":     node.description,
            "result_count":   0,
            "coverage_notes": f"FAILED: {error}",
            "fallback_used":  False,
        }, NodeStatus.FAILED, 0.0

    def _notes(self, n: int) -> str:
        if n == 0:
            return "No results found"
        if n < self.min_ok:
            return f"{n} result(s) — below minimum ({self.min_ok} required for OK)"
        return f"{n} result(s) found"

    def _depth_n(self, node: PlanNode, default: int = 10) -> int:
        """Map node.depth_override → max_results."""
        return {"shallow": 5, "standard": 10, "deep": 20}.get(
            node.depth_override or "", default
        )

    def _register_all(self, sources: list[dict], node: PlanNode, ctx) -> list[dict]:
        """Register a list of sources and mutate each with citation_id. Returns sources."""
        cit_reg = getattr(ctx, "citation_registry", None)
        if cit_reg is not None:
            for src in sources:
                cid = cit_reg.register(src, self.name, node.output_slot)
                src["citation_id"] = cid
        return sources

    def _build_output(
        self,
        sources: list[dict],
        node: PlanNode,
        coverage_notes: str | None = None,
        fallback_used: bool = False,
    ) -> tuple[dict, NodeStatus, float]:
        n = len(sources)
        status = (NodeStatus.OK      if n >= self.min_ok else
                  NodeStatus.PARTIAL if n > 0           else
                  NodeStatus.FAILED)
        avg_cred = (sum(s.get("credibility_base", 0.75) for s in sources) / n
                    if n else 0.0)
        return {
            "skill_name":     self.name,
            "sources":        sources,
            "query_used":     node.description,
            "result_count":   n,
            "coverage_notes": coverage_notes or self._notes(n),
            "fallback_used":  fallback_used,
        }, status, avg_cred

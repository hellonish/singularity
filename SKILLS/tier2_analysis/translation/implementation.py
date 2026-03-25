"""
translation — tool-based translation using TranslationTool.
Not LLM-based; calls the translation tool directly.
"""
from orchestrator.skills import SkillBase
from orchestrator.models import NodeStatus
from tools.translation import TranslationTool


class TranslationSkill(SkillBase):
    name = "translation"

    async def run(self, node, ctx, client, registry):
        tool = TranslationTool()
        target_lang = ctx.language or "en"

        # Gather text to translate from upstream
        texts = []
        for dep_id in node.depends_on:
            for slot, result in ctx.results.items():
                if dep_id in slot:
                    if isinstance(result, dict):
                        texts.append(result.get("summary", ""))
                    elif isinstance(result, str):
                        texts.append(result[:2000])

        if not texts:
            return {
                "summary": "No text found to translate",
                "findings": [],
                "citations_used": [],
                "confidence": 0.0,
                "coverage_gaps": ["no upstream text"],
                "upstream_slots_consumed": [],
            }, NodeStatus.PARTIAL, 0.5

        translated_findings = []
        for text in texts:
            if not text.strip():
                continue
            try:
                result = await tool.call_with_retry(text, target=target_lang)
                translated_findings.append({
                    "original": text[:200],
                    "translated": result.content[:500],
                    "confidence": result.credibility_base,
                })
            except Exception:
                pass

        avg_conf = (
            sum(f["confidence"] for f in translated_findings) / len(translated_findings)
            if translated_findings else 0.5
        )
        return {
            "skill_name": self.name,
            "summary": f"Translated {len(translated_findings)} text(s) to {target_lang}",
            "findings": translated_findings,
            "citations_used": [],
            "confidence": avg_conf,
            "coverage_gaps": [],
            "upstream_slots_consumed": list(ctx.results.keys()),
        }, NodeStatus.OK, avg_conf

"""Evidence ordering: what survives the per-node budget cuts.

The resolver and answerer both truncate evidence to a strength-scaled budget,
so ranking decides whether the model sees fetched full-text pages or only the
search snippets that happened to arrive first.
"""
import asyncio
from types import SimpleNamespace

from engine.research_workflow.agents import LLMAnswerer
from engine.research_workflow.dag import ResearchNode
from engine.research_workflow.evidence import rank_evidence
from engine.research_workflow.resolver import BoundedResearchResolver


def _record(url: str, content: str, credibility: float = 0.5) -> dict:
    return {"query": "q", "content": content, "title": url, "url": url, "credibility": credibility}


def test_rank_evidence_puts_full_text_ahead_of_snippets():
    snippet = _record("https://a.example", "short snippet", credibility=0.9)
    full_text = _record("https://b.example", "x" * 5_000, credibility=0.3)

    ranked = rank_evidence([snippet, full_text])

    assert ranked[0]["url"] == "https://b.example"


def test_rank_evidence_breaks_snippet_ties_by_credibility():
    low = _record("https://low.example", "snippet one", credibility=0.2)
    high = _record("https://high.example", "snippet two", credibility=0.9)

    ranked = rank_evidence([low, high])

    assert ranked[0]["url"] == "https://high.example"


def test_rank_evidence_dedupes_by_url_keeping_the_fuller_record():
    snippet = _record("https://page.example", "snippet")
    fetched = _record("https://page.example", "y" * 3_000)

    ranked = rank_evidence([snippet, fetched])

    assert len(ranked) == 1
    assert ranked[0]["content"] == "y" * 3_000


def test_resolver_returns_fetched_pages_ahead_of_snippet_floods():
    """A domain tool returning many snippets first must not displace the
    fetched full-text pages once the answerer truncates to its budget."""

    class SnippetHeavyExecutor:
        async def execute(self, invocation):
            if invocation.tool_name == "web_search":
                return SimpleNamespace(
                    content="search results",
                    sources=[
                        {"title": f"Result {i}", "url": f"https://result{i}.example", "snippet": f"snippet {i}"}
                        for i in range(6)
                    ],
                )
            return SimpleNamespace(
                content="full extracted page text " * 200,
                sources=[{"title": "Fetched", "url": invocation.arguments["url"], "snippet": "page"}],
            )

    async def answerer(node, evidence):
        return {"answer": "notes", "answered": True}

    result = asyncio.run(
        BoundedResearchResolver(SnippetHeavyExecutor(), answerer)(
            ResearchNode(node_id="n1", question="question", section_id="s1", level=0), 4
        )
    )

    assert result["answered"] is True
    # Both fetched pages outrank every remaining snippet-only record.
    top_two = [item["content"] for item in result["evidence"][:2]]
    assert all(content.startswith("full extracted page text") for content in top_two)


def test_answerer_keeps_full_text_within_its_evidence_budget():
    """rank-then-truncate: the fetched page survives even when snippets came
    first, and the discarded snippet never reaches the prompt."""

    class CapturingModel:
        def __init__(self):
            self.prompts = []

        async def complete(self, prompt: str, *, max_output_tokens: int) -> str:
            self.prompts.append(prompt)
            return '{"answer":"notes","unresolved_gaps":[]}'

    model = CapturingModel()
    caps = SimpleNamespace(max_evidence_per_node=2, max_source_chars=12_000, answer_completion_tokens=1_200)
    evidence = [
        _record("https://keep-snippet.example", "KEPT-SNIPPET", credibility=0.9),
        _record("https://drop-snippet.example", "DROPPED-SNIPPET", credibility=0.1),
        _record("https://full.example", "FULL-TEXT " * 500, credibility=0.5),
    ]

    result = asyncio.run(
        LLMAnswerer(model, caps)(
            ResearchNode(node_id="n1", question="question", section_id="s1", level=0), evidence
        )
    )

    assert result["answer"] == "notes"
    prompt = model.prompts[0]
    assert "FULL-TEXT" in prompt
    assert "KEPT-SNIPPET" in prompt
    assert "DROPPED-SNIPPET" not in prompt

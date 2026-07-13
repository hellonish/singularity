import asyncio

from engine.research_workflow.caps import RunCaps
from engine.research_workflow.dag import ResearchDAG, ResearchNode, ResearchNodeStatus
from engine.research_workflow.agents import LLMLead, LLMPlanner, LLMQA, LLMWriter
from engine.llm.groq import ProviderError
from engine.research_workflow.runner import TerminalResearchModel


class CapturingProvider:
    def __init__(self) -> None:
        self.config = None

    async def complete(self, *, config, **kwargs):
        self.config = config
        return type("Completion", (), {"content": '{"ok":true}'})()


class FakeModel:
    async def complete(self, prompt: str, *, max_output_tokens: int) -> str:
        if "Preserve the user's intent" in prompt:
            return '{"query":"bounded research","audience":"engineer","constraints":["cited"]}'
        if "Perspective:" in prompt:
            return '{"nodes":[{"question":"What is the bounded workflow?","rationale":"scope","section_id":"overview","level":0,"acceptance_criteria":["cited"],"expected_evidence":["primary"]}]}'
        if "Suggest at most two focused gaps" in prompt:
            return '{"passed":false,"score":0.4,"gaps":["missing limits"],"suggestions":[{"question":"What is the tool limit?","rationale":"bound"},{"question":"What is the QA limit?","rationale":"bound"},{"question":"A third question must be capped","rationale":"bound"}]}'
        if "Design a coherent report outline" in prompt:
            return '''{
                "title":"Bounded research",
                "limitations":[],
                "sections":[{"section_id":"overview","title":"Overview","node_ids":["root"]}]
            }'''
        if "a single ResearchDocumentV1 section object" in prompt:
            return '''{
                "section_id":"overview",
                "title":"Overview",
                "blocks":[{"kind":"paragraph","text":"The workflow is bounded.","reference_ids":["S1234567890"]}]
            }'''
        if "ResearchDocumentV1" in prompt:
            return '''{
                "schema_version":"research-document-v1",
                "title":"Bounded research",
                "query":"bounded research",
                "sections":[{"section_id":"overview","title":"Overview","blocks":[{"kind":"paragraph","text":"The workflow is bounded.","reference_ids":["S1234567890"]}]}],
                "references":[{"tag":"S1234567890","name":"Primary source","title":"Primary source","url":"https://example.test/source"}],
                "limitations":[]
            }'''
        raise AssertionError(f"unexpected prompt: {prompt}")


def test_terminal_research_uses_low_reasoning_for_gpt_oss_json_completions() -> None:
    provider = CapturingProvider()
    model = TerminalResearchModel(
        api_key="test-key",
        model_id="openai/gpt-oss-20b",
        caps=RunCaps.for_strength(1),
        provider=provider,
    )

    content = asyncio.run(model.complete("Return JSON only", max_output_tokens=500))

    assert content == '{"ok":true}'
    assert provider.config.reasoning_effort == "low"
    assert provider.config.max_output_tokens == 6_000


def test_terminal_research_omits_reasoning_effort_for_other_models() -> None:
    provider = CapturingProvider()
    model = TerminalResearchModel(
        api_key="test-key",
        provider_name="openrouter",
        model_id="openai/gpt-4.1-mini",
        caps=RunCaps.for_strength(1),
        provider=provider,
    )

    asyncio.run(model.complete("Return JSON only", max_output_tokens=500))

    assert provider.config.provider == "openrouter"
    assert provider.config.model_id == "openai/gpt-4.1-mini"
    assert provider.config.max_output_tokens == 1_200
    assert provider.config.reasoning_effort is None


def test_terminal_research_retries_retryable_failures_with_raised_budget() -> None:
    class FlakyProvider:
        def __init__(self) -> None:
            self.budgets = []

        async def complete(self, *, config, **kwargs):
            self.budgets.append(config.max_output_tokens)
            if len(self.budgets) == 1:
                raise ProviderError(code="provider_invalid_structured_output", message="bad JSON", retryable=True)
            return type("Completion", (), {"content": '{"ok":true}'})()

    provider = FlakyProvider()
    model = TerminalResearchModel(
        api_key="test-key",
        provider_name="openrouter",
        model_id="deepseek/deepseek-v4-flash",
        caps=RunCaps.for_strength(1),
        provider=provider,
    )

    content = asyncio.run(model.complete("Return JSON only", max_output_tokens=1_200))

    assert content == '{"ok":true}'
    assert provider.budgets == [1_200, 2_400]


def test_terminal_research_does_not_retry_non_retryable_failures() -> None:
    class DeadProvider:
        def __init__(self) -> None:
            self.calls = 0

        async def complete(self, **kwargs):
            self.calls += 1
            raise ProviderError(code="provider_credential_invalid", message="bad key", retryable=False)

    provider = DeadProvider()
    model = TerminalResearchModel(
        api_key="test-key",
        provider_name="openrouter",
        model_id="deepseek/deepseek-v4-flash",
        caps=RunCaps.for_strength(1),
        provider=provider,
    )

    try:
        asyncio.run(model.complete("Return JSON only", max_output_tokens=500))
    except ProviderError:
        pass
    else:
        raise AssertionError("non-retryable failure must propagate")
    assert provider.calls == 1


def test_planner_runs_three_named_perspectives_and_lead_deduplicates_nodes() -> None:
    planner = LLMPlanner(FakeModel())
    polished = asyncio.run(planner.polish_prompt("  bounded research  "))
    proposals = asyncio.run(planner.parallel_proposals(polished["query"]))
    dag = asyncio.run(LLMLead().merge(polished["query"], proposals, RunCaps.for_strength(1)))

    assert [proposal["perspective"] for proposal in proposals] == ["coverage", "evidence-risk", "narrative"]
    assert len(dag.nodes) == 1


def test_planner_can_limit_perspectives_for_quick_research() -> None:
    proposals = asyncio.run(LLMPlanner(FakeModel(), max_perspectives=1).parallel_proposals("bounded research"))

    assert [proposal["perspective"] for proposal in proposals] == ["coverage"]


def test_qa_accepts_no_more_than_two_suggestions_per_section() -> None:
    caps = RunCaps.for_strength(2)
    dag = ResearchDAG()
    dag.add_node(
        ResearchNode(
            node_id="root", question="What is bounded research?", section_id="overview", level=0,
            status=ResearchNodeStatus.ANSWERED, answer="A bounded workflow.",
        ),
        caps,
    )

    reviews = asyncio.run(LLMQA(FakeModel()).review(dag, caps))

    assert len(reviews[0]["accepted_suggestions"]) == 2
    assert len(dag.nodes) == 3
    assert dag.nodes["root"].status == ResearchNodeStatus.QA_FAILED


def test_writer_keeps_valid_citable_source_references() -> None:
    caps = RunCaps.for_strength(1)
    dag = ResearchDAG()
    dag.add_node(
        ResearchNode(
            node_id="root", question="What is bounded research?", section_id="overview", level=0,
            status=ResearchNodeStatus.PASSED, answer="A bounded workflow.",
            source_records=[{
                "tag": "S1234567890", "name": "Primary source", "title": "Primary source",
                "url": "https://example.test/source", "source_type": "web",
            }],
        ),
        caps,
    )

    document = asyncio.run(LLMWriter(FakeModel()).write(dag, "bounded research"))

    assert document["references"][0]["tag"] == "S1234567890"
    assert document["sections"][0]["blocks"][0]["reference_ids"] == ["S1234567890"]


def test_writer_falls_back_to_completed_cited_evidence_after_provider_failure() -> None:
    class FailingModel:
        async def complete(self, prompt: str, *, max_output_tokens: int) -> str:
            raise ProviderError(code="provider_invalid_json_response", message="invalid JSON", retryable=True)

    caps = RunCaps.for_strength(1)
    dag = ResearchDAG()
    dag.add_node(ResearchNode(
        node_id="root", question="What happened?", section_id="overview", level=0,
        status=ResearchNodeStatus.ANSWERED, answer="A supported finding.",
        source_records=[{"tag": "S1234567890", "name": "Primary", "title": "Primary", "url": "https://example.test/source", "source_type": "web"}],
    ), caps)

    document = asyncio.run(LLMWriter(FailingModel()).write(dag, "What happened?"))

    assert document["title"] == "Research report (fallback assembly)"
    assert document["sections"][0]["blocks"][0]["reference_ids"] == ["S1234567890"]
